/**
 * PotholeNet v2.3 - Native Bridge Core
 * 
 * C++ Signal Processing Library for Real-time Mobile Detection
 * Optimized 4th-order Butterworth High-pass Filter for 3-axis Accelerometer Data
 */

#include "potholenet_core.h"
#include <cmath>
#include <vector>
#include <algorithm>
#include <memory>

// Butterworth Filter Implementation
class ButterworthFilter {
private:
    // Filter coefficients
    std::vector<double> a_coeffs;  // Denominator coefficients
    std::vector<double> b_coeffs;  // Numerator coefficients
    
    // Delay lines for each axis
    std::vector<double> x_history_x;
    std::vector<double> y_history_x;
    std::vector<double> x_history_y;
    std::vector<double> y_history_y;
    std::vector<double> x_history_z;
    std::vector<double> y_history_z;
    
    // Filter parameters
    double cutoff_freq;
    double sample_rate;
    int filter_order;
    
    // Precomputed constants for performance
    double nyquist_freq;
    double normalized_cutoff;
    
public:
    ButterworthFilter(double sample_rate, double cutoff_freq, int order = 4)
        : sample_rate(sample_rate), cutoff_freq(cutoff_freq), filter_order(order) {
        
        nyquist_freq = sample_rate / 2.0;
        normalized_cutoff = cutoff_freq / nyquist_freq;
        
        // Initialize coefficient vectors
        a_coeffs.resize(order + 1);
        b_coeffs.resize(order + 1);
        
        // Initialize delay lines
        x_history_x.resize(order + 1, 0.0);
        y_history_x.resize(order + 1, 0.0);
        x_history_y.resize(order + 1, 0.0);
        y_history_y.resize(order + 1, 0.0);
        x_history_z.resize(order + 1, 0.0);
        y_history_z.resize(order + 1, 0.0);
        
        // Calculate Butterworth coefficients
        calculate_butterworth_coefficients();
    }
    
private:
    void calculate_butterworth_coefficients() {
        // Calculate 4th-order Butterworth high-pass filter coefficients
        // Using bilinear transform with pre-warping
        
        const double order = 4.0;
        const double pi = 3.14159265358979323846;
        
        // Pre-warp the cutoff frequency
        double warped_cutoff = 2.0 * sample_rate * std::tan(pi * normalized_cutoff / sample_rate);
        
        // Calculate poles for Butterworth filter
        std::vector<std::complex<double>> poles;
        for (int k = 1; k <= order; ++k) {
            double angle = (2.0 * k - 1.0) * pi / (2.0 * order);
            std::complex<double> pole = std::polar(1.0, angle);
            poles.push_back(pole);
        }
        
        // Apply bilinear transform to get digital filter coefficients
        // For high-pass filter, we invert the low-pass prototype
        
        // Simplified coefficient calculation for 4th-order Butterworth high-pass
        // These are pre-calculated for optimal performance
        const double alpha = std::tan(pi * normalized_cutoff);
        const double alpha2 = alpha * alpha;
        const double sqrt2_alpha = std::sqrt(2.0) * alpha;
        
        // Denominator coefficients (a)
        a_coeffs[0] = 1.0;
        a_coeffs[1] = -4.0 * (alpha2 - 2.0) / (alpha2 + sqrt2_alpha + 1.0);
        a_coeffs[2] = 6.0 * (alpha2 - 2.0) / (alpha2 + sqrt2_alpha + 1.0);
        a_coeffs[3] = -4.0 * (alpha2 - 2.0) / (alpha2 + sqrt2_alpha + 1.0);
        a_coeffs[4] = (alpha2 - sqrt2_alpha + 1.0) / (alpha2 + sqrt2_alpha + 1.0);
        
        // Numerator coefficients (b) for high-pass
        double denominator = alpha2 + sqrt2_alpha + 1.0;
        b_coeffs[0] = 1.0;
        b_coeffs[1] = -4.0;
        b_coeffs[2] = 6.0;
        b_coeffs[3] = -4.0;
        b_coeffs[4] = 1.0;
        
        // Normalize coefficients
        for (int i = 0; i <= filter_order; ++i) {
            b_coeffs[i] /= denominator;
        }
    }
    
    // Optimized filter function for single axis
    inline double filter_axis(double input, 
                            std::vector<double>& x_history, 
                            std::vector<double>& y_history) {
        // Shift delay lines
        for (int i = filter_order; i > 0; --i) {
            x_history[i] = x_history[i - 1];
            y_history[i] = y_history[i - 1];
        }
        
        // Add new input
        x_history[0] = input;
        
        // Calculate filtered output
        double output = 0.0;
        
        // Apply numerator coefficients (b)
        for (int i = 0; i <= filter_order; ++i) {
            output += b_coeffs[i] * x_history[i];
        }
        
        // Apply denominator coefficients (a)
        for (int i = 1; i <= filter_order; ++i) {
            output -= a_coeffs[i] * y_history[i];
        }
        
        // Store output
        y_history[0] = output;
        
        return output;
    }
    
public:
    // Process 3-axis accelerometer data
    void process_3axis(double x_in, double y_in, double z_in, 
                      double& x_out, double& y_out, double& z_out) {
        x_out = filter_axis(x_in, x_history_x, y_history_x);
        y_out = filter_axis(y_in, x_history_y, y_history_y);
        z_out = filter_axis(z_in, x_history_z, y_history_z);
    }
    
    // Reset filter state
    void reset() {
        std::fill(x_history_x.begin(), x_history_x.end(), 0.0);
        std::fill(y_history_x.begin(), y_history_x.end(), 0.0);
        std::fill(x_history_y.begin(), x_history_y.end(), 0.0);
        std::fill(y_history_y.begin(), y_history_y.end(), 0.0);
        std::fill(x_history_z.begin(), x_history_z.end(), 0.0);
        std::fill(y_history_z.begin(), y_history_z.end(), 0.0);
    }
    
    // Get filter parameters
    double get_cutoff_frequency() const { return cutoff_freq; }
    double get_sample_rate() const { return sample_rate; }
    int get_order() const { return filter_order; }
};

// Main Signal Processor Class
class SignalProcessor {
private:
    std::unique_ptr<ButterworthFilter> filter;
    double sample_rate;
    double cutoff_frequency;
    
    // Feature extraction buffers
    std::vector<double> z_buffer;
    std::vector<double> magnitude_buffer;
    size_t buffer_size;
    size_t buffer_index;
    
    // Detection state
    bool detection_active;
    double detection_threshold;
    double current_magnitude;
    
    // Performance tracking
    uint64_t samples_processed;
    double last_process_time;
    
public:
    SignalProcessor(double frequency, double cutoff)
        : sample_rate(frequency), cutoff_frequency(cutoff), 
          buffer_size(128), buffer_index(0), detection_active(false),
          detection_threshold(2.5), current_magnitude(0.0),
          samples_processed(0), last_process_time(0.0) {
        
        // Ensure buffer_size is power of 2 for fast modulo
        if (buffer_size & (buffer_size - 1)) {
            buffer_size = 128; // Next power of 2 >= 100
        }
        
        // Initialize Butterworth filter
        filter = std::make_unique<ButterworthFilter>(sample_rate, cutoff_frequency);
        
        // Initialize buffers (fixed size, no reallocation)
        z_buffer.resize(buffer_size, 0.0);
        magnitude_buffer.resize(buffer_size, 0.0);
    }
    
    bool process_sample(double x, double y, double z) {
        // Apply high-pass filter
        double x_filtered, y_filtered, z_filtered;
        filter->process_3axis(x, y, z, z_filtered, y_filtered, x_filtered);
        
        // Calculate magnitude (optimized sqrt)
        double magnitude = std::sqrt(x_filtered * x_filtered + 
                                    y_filtered * y_filtered + 
                                    z_filtered * z_filtered);
        
        // Store in circular buffer (no bounds checking for performance)
        z_buffer[buffer_index] = z_filtered;
        magnitude_buffer[buffer_index] = magnitude;
        buffer_index = (buffer_index + 1) & (buffer_size - 1); // Faster modulo for power of 2
        
        current_magnitude = magnitude;
        
        // Simple detection logic (can be enhanced with ML models)
        bool detected = magnitude > detection_threshold;
        
        samples_processed++;
        
        return detected;
    }
    
    // Get current filtered magnitude
    double get_current_magnitude() const {
        return current_magnitude;
    }
    
    // Get Z-axis variance (for feature extraction)
    double get_z_variance() const {
        if (samples_processed < buffer_size) {
            return 0.0;
        }
        
        double mean = 0.0;
        const double* z_data = z_buffer.data();
        for (size_t i = 0; i < buffer_size; ++i) {
            mean += z_data[i];
        }
        mean /= static_cast<double>(buffer_size);
        
        double variance = 0.0;
        for (size_t i = 0; i < buffer_size; ++i) {
            double diff = z_data[i] - mean;
            variance += diff * diff;
        }
        variance /= static_cast<double>(buffer_size);
        
        return variance;
    }
    
    // Get peak-to-peak magnitude
    double get_peak_to_peak() const {
        if (samples_processed < buffer_size) {
            return 0.0;
        }
        
        const double* mag_data = magnitude_buffer.data();
        double min_val = mag_data[0];
        double max_val = mag_data[0];
        
        for (size_t i = 1; i < buffer_size; ++i) {
            if (mag_data[i] < min_val) min_val = mag_data[i];
            if (mag_data[i] > max_val) max_val = mag_data[i];
        }
        
        return max_val - min_val;
    }
    
    // Reset processor state
    void reset() {
        filter->reset();
        std::fill(z_buffer.begin(), z_buffer.end(), 0.0);
        std::fill(magnitude_buffer.begin(), magnitude_buffer.end(), 0.0);
        buffer_index = 0;
        samples_processed = 0;
        current_magnitude = 0.0;
    }
    
    // Configuration methods
    void set_detection_threshold(double threshold) {
        detection_threshold = threshold;
    }
    
    void set_buffer_size(size_t size) {
        buffer_size = size;
        z_buffer.resize(buffer_size, 0.0);
        magnitude_buffer.resize(buffer_size, 0.0);
        buffer_index = 0;
    }
    
    // Get processor info
    double get_sample_rate() const { return sample_rate; }
    double get_cutoff_frequency() const { return cutoff_frequency; }
    uint64_t get_samples_processed() const { return samples_processed; }
    double get_last_process_time_ms() const { return last_process_time; }
};

// C-compatible FFI Implementation
extern "C" {

#ifdef _WIN32
#define EXPORT __declspec(dllexport)
#else
#define EXPORT
#endif

EXPORT void* create_processor(double frequency, double cutoff) {
    try {
        return static_cast<void*>(new SignalProcessor(frequency, cutoff));
    } catch (...) {
        return nullptr;
    }
}

EXPORT bool process_sample(void* processor, double x, double y, double z) {
    if (!processor) {
        return false;
    }
    
    try {
        SignalProcessor* proc = static_cast<SignalProcessor*>(processor);
        return proc->process_sample(x, y, z);
    } catch (...) {
        return false;
    }
}

EXPORT void destroy_processor(void* processor) {
    if (processor) {
        try {
            delete static_cast<SignalProcessor*>(processor);
        } catch (...) {
            // Ignore exceptions during cleanup
        }
    }
}

// Additional FFI functions for enhanced functionality
EXPORT double get_current_magnitude(void* processor) {
    if (!processor) {
        return 0.0;
    }
    
    try {
        SignalProcessor* proc = static_cast<SignalProcessor*>(processor);
        return proc->get_current_magnitude();
    } catch (...) {
        return 0.0;
    }
}

EXPORT double get_z_variance(void* processor) {
    if (!processor) {
        return 0.0;
    }
    
    try {
        SignalProcessor* proc = static_cast<SignalProcessor*>(processor);
        return proc->get_z_variance();
    } catch (...) {
        return 0.0;
    }
}

EXPORT double get_peak_to_peak(void* processor) {
    if (!processor) {
        return 0.0;
    }
    
    try {
        SignalProcessor* proc = static_cast<SignalProcessor*>(processor);
        return proc->get_peak_to_peak();
    } catch (...) {
        return 0.0;
    }
}

EXPORT void reset_processor(void* processor) {
    if (!processor) {
        return;
    }
    
    try {
        SignalProcessor* proc = static_cast<SignalProcessor*>(processor);
        proc->reset();
    } catch (...) {
        // Ignore exceptions during reset
    }
}

EXPORT void set_detection_threshold(void* processor, double threshold) {
    if (!processor) {
        return;
    }
    
    try {
        SignalProcessor* proc = static_cast<SignalProcessor*>(processor);
        proc->set_detection_threshold(threshold);
    } catch (...) {
        // Ignore exceptions during configuration
    }
}

EXPORT bool is_processor_valid(void* processor) {
    return processor != nullptr;
}

} // extern "C"
