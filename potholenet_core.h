/**
 * PotholeNet v2.3 - Native Bridge Header
 * 
 * C-compatible FFI interface for Flutter integration
 * Cross-platform signal processing library for mobile devices
 */

#ifndef POTHOLENET_CORE_H
#define POTHOLENET_CORE_H

#ifdef __cplusplus
extern "C" {
#endif

// Platform-specific export declarations
#if defined(_WIN32) || defined(_WIN64)
    #ifdef POTHOLENET_CORE_EXPORTS
        #define POTHOLENET_API __declspec(dllexport)
    #else
        #define POTHOLENET_API __declspec(dllimport)
    #endif
#else
    #if defined(__GNUC__) || defined(__clang__)
        #define POTHOLENET_API __attribute__((visibility("default")))
    #else
        #define POTHOLENET_API
    #endif
#endif

// Core processor lifecycle functions
/**
 * Create a new signal processor instance
 * 
 * @param frequency Sample frequency in Hz (e.g., 100.0 for 100Hz)
 * @param cutoff Cutoff frequency for high-pass filter in Hz (e.g., 12.0)
 * @return Pointer to processor instance, or nullptr on failure
 */
POTHOLENET_API void* create_processor(double frequency, double cutoff);

/**
 * Process a single 3-axis accelerometer sample
 * 
 * @param processor Pointer to processor instance
 * @param x X-axis acceleration value
 * @param y Y-axis acceleration value  
 * @param z Z-axis acceleration value
 * @return true if pothole detected, false otherwise
 */
POTHOLENET_API bool process_sample(void* processor, double x, double y, double z);

/**
 * Destroy processor instance and free memory
 * 
 * @param processor Pointer to processor instance
 */
POTHOLENET_API void destroy_processor(void* processor);

// Enhanced functionality for Flutter integration
/**
 * Get current filtered magnitude from processor
 * 
 * @param processor Pointer to processor instance
 * @return Current magnitude value
 */
POTHOLENET_API double get_current_magnitude(void* processor);

/**
 * Get Z-axis variance for feature extraction
 * 
 * @param processor Pointer to processor instance
 * @return Z-axis variance value
 */
POTHOLENET_API double get_z_variance(void* processor);

/**
 * Get peak-to-peak magnitude for feature extraction
 * 
 * @param processor Pointer to processor instance
 * @return Peak-to-peak magnitude value
 */
POTHOLENET_API double get_peak_to_peak(void* processor);

/**
 * Reset processor state and clear buffers
 * 
 * @param processor Pointer to processor instance
 */
POTHOLENET_API void reset_processor(void* processor);

/**
 * Set detection threshold for pothole detection
 * 
 * @param processor Pointer to processor instance
 * @param threshold Detection threshold value
 */
POTHOLENET_API void set_detection_threshold(void* processor, double threshold);

/**
 * Check if processor instance is valid
 * 
 * @param processor Pointer to processor instance
 * @return true if valid, false otherwise
 */
POTHOLENET_API bool is_processor_valid(void* processor);

// Constants and configuration
#define POTHOLENET_VERSION_MAJOR 2
#define POTHOLENET_VERSION_MINOR 3
#define POTHOLENET_VERSION_PATCH 0

// Default configuration values
#define POTHOLENET_DEFAULT_SAMPLE_RATE 100.0    // 100Hz
#define POTHOLENET_DEFAULT_CUTOFF_FREQ 12.0     // 12Hz high-pass
#define POTHOLENET_DEFAULT_THRESHOLD 2.5        // Detection threshold
#define POTHOLENET_BUFFER_SIZE 100              // Sample buffer size

// Error codes
typedef enum {
    POTHOLENET_SUCCESS = 0,
    POTHOLENET_ERROR_NULL_POINTER = -1,
    POTHOLENET_ERROR_INVALID_PARAMETER = -2,
    POTHOLENET_ERROR_MEMORY_ALLOCATION = -3,
    POTHOLENET_ERROR_PROCESSING = -4
} potholenet_error_t;

// Result structure for enhanced API calls
typedef struct {
    bool detected;
    double magnitude;
    double z_variance;
    double peak_to_peak;
    potholenet_error_t error_code;
} potholenet_result_t;

// Advanced API functions (optional for future enhancement)
/**
 * Process sample and return detailed results
 * 
 * @param processor Pointer to processor instance
 * @param x X-axis acceleration value
 * @param y Y-axis acceleration value
 * @param z Z-axis acceleration value
 * @param result Pointer to result structure to fill
 * @return Error code
 */
POTHOLENET_API potholenet_error_t process_sample_advanced(
    void* processor, 
    double x, 
    double y, 
    double z, 
    potholenet_result_t* result
);

/**
 * Get processor configuration information
 * 
 * @param processor Pointer to processor instance
 * @param sample_rate Output for sample rate
 * @param cutoff_freq Output for cutoff frequency
 * @return Error code
 */
POTHOLENET_API potholenet_error_t get_processor_config(
    void* processor,
    double* sample_rate,
    double* cutoff_freq
);

/**
 * Get performance statistics
 * 
 * @param processor Pointer to processor instance
 * @param samples_processed Output for samples processed count
 * @param avg_process_time_ms Output for average processing time in milliseconds
 * @return Error code
 */
POTHOLENET_API potholenet_error_t get_performance_stats(
    void* processor,
    uint64_t* samples_processed,
    double* avg_process_time_ms
);

// Utility functions
/**
 * Get library version as string
 * 
 * @return Version string (e.g., "2.3.0")
 */
POTHOLENET_API const char* get_version_string(void);

/**
 * Check if library supports specific features
 * 
 * @param feature Feature name to check
 * @return true if supported, false otherwise
 */
POTHOLENET_API bool supports_feature(const char* feature);

#ifdef __cplusplus
}
#endif

#endif // POTHOLENET_CORE_H
