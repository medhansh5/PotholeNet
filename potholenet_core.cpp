/**
 * PotholeNet v3.0 - Native Bridge Core
 * 
 * C++ Signal Processing Library for Real-time Mobile Detection
 * Optimized 4th-order Butterworth High-pass Filter (Biquad SOS Cascade) for 3-axis Accelerometer Data
 * Zero-allocation hot path, SIMD-friendly Direct Form II Transposed structure, and full NDK compatibility (-fno-exceptions).
 */

#include "potholenet_core.h"
#include <cmath>
#include <vector>
#include <algorithm>
#include <memory>
#include <atomic>
#include <cstring>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

// Second-Order Section (Biquad) using Direct Form II Transposed
// Numerically stable for high-pass filtering at high sampling rates
struct BiquadSection {
    double b0, b1, b2;
    double a1, a2;
    double z1_x, z2_x;
    double z1_y, z2_y;
    double z1_z, z2_z;

    BiquadSection() {
        b0 = 1.0; b1 = 0.0; b2 = 0.0;
        a1 = 0.0; a2 = 0.0;
        reset();
    }

    void reset() {
        z1_x = z2_x = 0.0;
        z1_y = z2_y = 0.0;
        z1_z = z2_z = 0.0;
    }

    inline double process_axis(double in, double& z1, double& z2) {
        double out = b0 * in + z1;
        z1 = b1 * in - a1 * out + z2;
        z2 = b2 * in - a2 * out;
        return out;
    }

    void process_3axis(double x_in, double y_in, double z_in,
                       double& x_out, double& y_out, double& z_out) {
        x_out = process_axis(x_in, z1_x, z2_x);
        y_out = process_axis(y_in, z1_y, z2_y);
        z_out = process_axis(z_in, z1_z, z2_z);
    }
};

// 4th-Order Butterworth High-Pass Filter implemented as a cascade of two Biquad sections
class ButterworthFilter {
private:
    BiquadSection section1;
    BiquadSection section2;
    double sample_rate;
    double cutoff_freq;

public:
    ButterworthFilter(double sample_rate, double cutoff_freq)
        : sample_rate(sample_rate), cutoff_freq(cutoff_freq) {
        calculate_coefficients();
    }

    void calculate_coefficients() {
        // Pre-warp cutoff frequency for exact bilinear transformation
        double nyquist = sample_rate * 0.5;
        double norm_cutoff = cutoff_freq / nyquist;
        if (norm_cutoff >= 0.99) norm_cutoff = 0.99;
        if (norm_cutoff <= 0.001) norm_cutoff = 0.001;

        double K = std::tan(M_PI * cutoff_freq / sample_rate);
        double K2 = K * K;

        // For a 4th-order Butterworth filter, the Q factors of the two Biquad sections are:
        // Q1 = 1 / (2 * cos(pi/8)) = 0.541196100146197
        // Q2 = 1 / (2 * cos(3*pi/8)) = 1.306562964876376
        const double Q1 = 0.541196100146197;
        const double Q2 = 1.306562964876376;

        // Section 1 coefficients (High-Pass Biquad)
        double norm1 = 1.0 + (K / Q1) + K2;
        section1.b0 = 1.0 / norm1;
        section1.b1 = -2.0 / norm1;
        section1.b2 = 1.0 / norm1;
        section1.a1 = 2.0 * (K2 - 1.0) / norm1;
        section1.a2 = (1.0 - (K / Q1) + K2) / norm1;

        // Section 2 coefficients (High-Pass Biquad)
        double norm2 = 1.0 + (K / Q2) + K2;
        section2.b0 = 1.0 / norm2;
        section2.b1 = -2.0 / norm2;
        section2.b2 = 1.0 / norm2;
        section2.a1 = 2.0 * (K2 - 1.0) / norm2;
        section2.a2 = (1.0 - (K / Q2) + K2) / norm2;
    }

    void process_3axis(double x_in, double y_in, double z_in,
                       double& x_out, double& y_out, double& z_out) {
        double x_mid, y_mid, z_mid;
        section1.process_3axis(x_in, y_in, z_in, x_mid, y_mid, z_mid);
        section2.process_3axis(x_mid, y_mid, z_mid, x_out, y_out, z_out);
    }

    void reset() {
        section1.reset();
        section2.reset();
    }

    double get_cutoff_frequency() const { return cutoff_freq; }
    double get_sample_rate() const { return sample_rate; }
};

// Helper function to enforce power-of-2 buffer sizes
static inline size_t next_power_of_2(size_t n) {
    if (n < 16) return 16;
    size_t p = 1;
    while (p < n && p < (1ULL << 30)) {
        p <<= 1;
    }
    return p;
}

// Main Signal Processor Class
class SignalProcessor {
private:
    std::unique_ptr<ButterworthFilter> filter;
    double sample_rate;
    double cutoff_frequency;
    
    // Feature extraction circular buffers (power of 2 size)
    std::vector<double> z_buffer;
    std::vector<double> magnitude_buffer;
    size_t buffer_size;
    size_t buffer_index;
    
    // Detection and metric state (atomic for thread-safe querying)
    std::atomic<double> detection_threshold;
    std::atomic<double> current_magnitude;
    std::atomic<uint64_t> samples_processed;
    std::atomic<double> last_process_time;
    
public:
    SignalProcessor(double frequency, double cutoff)
        : sample_rate(frequency), cutoff_frequency(cutoff), 
          buffer_size(128), buffer_index(0),
          detection_threshold(2.5), current_magnitude(0.0),
          samples_processed(0), last_process_time(0.0) {
        
        buffer_size = next_power_of_2(buffer_size);
        filter = std::make_unique<ButterworthFilter>(sample_rate, cutoff_frequency);
        z_buffer.assign(buffer_size, 0.0);
        magnitude_buffer.assign(buffer_size, 0.0);
    }
    
    bool process_sample(double x, double y, double z) {
        // Apply 4th-order Butterworth Biquad cascade filter
        // BUG FIX (Line 212): Correct parameter ordering so X goes to X and Z goes to Z
        double x_filtered, y_filtered, z_filtered;
        filter->process_3axis(x, y, z, x_filtered, y_filtered, z_filtered);
        
        // Calculate magnitude
        double magnitude = std::sqrt(x_filtered * x_filtered + 
                                     y_filtered * y_filtered + 
                                     z_filtered * z_filtered);
        
        // Store in circular buffer with bitwise AND modulo (guaranteed power of 2)
        z_buffer[buffer_index] = z_filtered;
        magnitude_buffer[buffer_index] = magnitude;
        buffer_index = (buffer_index + 1) & (buffer_size - 1);
        
        current_magnitude.store(magnitude, std::memory_order_release);
        
        // Check threshold against atomic threshold
        double thresh = detection_threshold.load(std::memory_order_acquire);
        bool detected = magnitude > thresh;
        
        samples_processed.fetch_add(1, std::memory_order_relaxed);
        
        return detected;
    }
    
    double get_current_magnitude() const {
        return current_magnitude.load(std::memory_order_acquire);
    }
    
    double get_z_variance() const {
        uint64_t count_64 = samples_processed.load(std::memory_order_acquire);
        size_t count = std::min(static_cast<size_t>(count_64), buffer_size);
        if (count < 2) {
            return 0.0;
        }
        
        double mean = 0.0;
        const double* z_data = z_buffer.data();
        for (size_t i = 0; i < count; ++i) {
            mean += z_data[i];
        }
        mean /= static_cast<double>(count);
        
        double variance = 0.0;
        for (size_t i = 0; i < count; ++i) {
            double diff = z_data[i] - mean;
            variance += diff * diff;
        }
        variance /= static_cast<double>(count);
        
        return variance;
    }
    
    double get_peak_to_peak() const {
        uint64_t count_64 = samples_processed.load(std::memory_order_acquire);
        size_t count = std::min(static_cast<size_t>(count_64), buffer_size);
        if (count < 1) {
            return 0.0;
        }
        
        const double* mag_data = magnitude_buffer.data();
        double min_val = mag_data[0];
        double max_val = mag_data[0];
        
        for (size_t i = 1; i < count; ++i) {
            if (mag_data[i] < min_val) min_val = mag_data[i];
            if (mag_data[i] > max_val) max_val = mag_data[i];
        }
        
        return max_val - min_val;
    }
    
    void reset() {
        filter->reset();
        std::fill(z_buffer.begin(), z_buffer.end(), 0.0);
        std::fill(magnitude_buffer.begin(), magnitude_buffer.end(), 0.0);
        buffer_index = 0;
        samples_processed.store(0, std::memory_order_release);
        current_magnitude.store(0.0, std::memory_order_release);
    }
    
    void set_detection_threshold(double threshold) {
        detection_threshold.store(threshold, std::memory_order_release);
    }
    
    void set_buffer_size(size_t size) {
        buffer_size = next_power_of_2(size);
        z_buffer.assign(buffer_size, 0.0);
        magnitude_buffer.assign(buffer_size, 0.0);
        buffer_index = 0;
        samples_processed.store(0, std::memory_order_release);
    }
    
    double get_sample_rate() const { return sample_rate; }
    double get_cutoff_frequency() const { return cutoff_frequency; }
    uint64_t get_samples_processed() const { return samples_processed.load(std::memory_order_acquire); }
    double get_last_process_time_ms() const { return last_process_time.load(std::memory_order_acquire); }
};

// C-compatible FFI Implementation (No try/catch blocks for -fno-exceptions compatibility)
extern "C" {

POTHOLENET_API void* create_processor(double frequency, double cutoff) {
    // Validate parameters to prevent division by zero or NaN propagation
    if (frequency <= 0.0 || cutoff <= 0.0 || cutoff >= frequency * 0.5) {
        return nullptr;
    }
    return static_cast<void*>(new SignalProcessor(frequency, cutoff));
}

POTHOLENET_API bool process_sample(void* processor, double x, double y, double z) {
    if (!processor) {
        return false;
    }
    SignalProcessor* proc = static_cast<SignalProcessor*>(processor);
    return proc->process_sample(x, y, z);
}

POTHOLENET_API void destroy_processor(void* processor) {
    if (processor) {
        delete static_cast<SignalProcessor*>(processor);
    }
}

POTHOLENET_API double get_current_magnitude(void* processor) {
    if (!processor) return 0.0;
    SignalProcessor* proc = static_cast<SignalProcessor*>(processor);
    return proc->get_current_magnitude();
}

POTHOLENET_API double get_z_variance(void* processor) {
    if (!processor) return 0.0;
    SignalProcessor* proc = static_cast<SignalProcessor*>(processor);
    return proc->get_z_variance();
}

POTHOLENET_API double get_peak_to_peak(void* processor) {
    if (!processor) return 0.0;
    SignalProcessor* proc = static_cast<SignalProcessor*>(processor);
    return proc->get_peak_to_peak();
}

POTHOLENET_API void reset_processor(void* processor) {
    if (!processor) return;
    SignalProcessor* proc = static_cast<SignalProcessor*>(processor);
    proc->reset();
}

POTHOLENET_API void set_detection_threshold(void* processor, double threshold) {
    if (!processor) return;
    SignalProcessor* proc = static_cast<SignalProcessor*>(processor);
    proc->set_detection_threshold(threshold);
}

POTHOLENET_API bool is_processor_valid(void* processor) {
    return processor != nullptr;
}

// Advanced API Functions previously missing from implementation
POTHOLENET_API potholenet_error_t process_sample_advanced(
    void* processor, 
    double x, 
    double y, 
    double z, 
    potholenet_result_t* result
) {
    if (!processor || !result) {
        return POTHOLENET_ERROR_NULL_POINTER;
    }
    
    SignalProcessor* proc = static_cast<SignalProcessor*>(processor);
    bool detected = proc->process_sample(x, y, z);
    
    result->detected = detected;
    result->magnitude = proc->get_current_magnitude();
    result->z_variance = proc->get_z_variance();
    result->peak_to_peak = proc->get_peak_to_peak();
    result->error_code = POTHOLENET_SUCCESS;
    
    return POTHOLENET_SUCCESS;
}

POTHOLENET_API potholenet_error_t get_processor_config(
    void* processor,
    double* sample_rate,
    double* cutoff_freq
) {
    if (!processor || !sample_rate || !cutoff_freq) {
        return POTHOLENET_ERROR_NULL_POINTER;
    }
    
    SignalProcessor* proc = static_cast<SignalProcessor*>(processor);
    *sample_rate = proc->get_sample_rate();
    *cutoff_freq = proc->get_cutoff_frequency();
    
    return POTHOLENET_SUCCESS;
}

POTHOLENET_API potholenet_error_t get_performance_stats(
    void* processor,
    uint64_t* samples_processed,
    double* avg_process_time_ms
) {
    if (!processor || !samples_processed || !avg_process_time_ms) {
        return POTHOLENET_ERROR_NULL_POINTER;
    }
    
    SignalProcessor* proc = static_cast<SignalProcessor*>(processor);
    *samples_processed = proc->get_samples_processed();
    *avg_process_time_ms = proc->get_last_process_time_ms();
    
    return POTHOLENET_SUCCESS;
}

POTHOLENET_API const char* get_version_string(void) {
    return "3.0.0";
}

POTHOLENET_API bool supports_feature(const char* feature) {
    if (!feature) return false;
    if (std::strcmp(feature, "spatial_aggregation") == 0) return true;
    if (std::strcmp(feature, "dbscan_clustering") == 0) return true;
    if (std::strcmp(feature, "native_bridge") == 0) return true;
    if (std::strcmp(feature, "simd_biquad") == 0) return true;
    if (std::strcmp(feature, "zero_allocation") == 0) return true;
    return false;
}

} // extern "C"
