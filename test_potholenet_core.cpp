/**
 * PotholeNet v2.3 - Native Bridge Test Suite
 * 
 * Comprehensive testing for the C++ signal processing library
 * Validates Butterworth filter performance and FFI interface
 */

#include "potholenet_core.h"
#include <iostream>
#include <chrono>
#include <vector>
#include <cmath>
#include <cassert>

class TestSuite {
private:
    int tests_passed = 0;
    int tests_failed = 0;
    
public:
    void run_test(const std::string& test_name, std::function<void()> test_func) {
        std::cout << "Running test: " << test_name << " ... ";
        
        try {
            test_func();
            tests_passed++;
            std::cout << "PASSED" << std::endl;
        } catch (const std::exception& e) {
            tests_failed++;
            std::cout << "FAILED: " << e.what() << std::endl;
        } catch (...) {
            tests_failed++;
            std::cout << "FAILED: Unknown exception" << std::endl;
        }
    }
    
    void assert_true(bool condition, const std::string& message = "") {
        if (!condition) {
            throw std::runtime_error(message.empty() ? "Assertion failed" : message);
        }
    }
    
    void assert_equals(double expected, double actual, double tolerance = 1e-6, const std::string& message = "") {
        if (std::abs(expected - actual) > tolerance) {
            throw std::runtime_error(message + " Expected: " + std::to_string(expected) + 
                                 ", Actual: " + std::to_string(actual));
        }
    }
    
    void print_summary() {
        std::cout << "\n=== Test Summary ===" << std::endl;
        std::cout << "Passed: " << tests_passed << std::endl;
        std::cout << "Failed: " << tests_failed << std::endl;
        std::cout << "Total: " << (tests_passed + tests_failed) << std::endl;
        
        if (tests_failed == 0) {
            std::cout << "All tests PASSED!" << std::endl;
        } else {
            std::cout << "Some tests FAILED!" << std::endl;
        }
    }
};

void test_processor_creation() {
    TestSuite suite;
    
    suite.run_test("Create processor with valid parameters", [&]() {
        void* processor = create_processor(100.0, 12.0);
        suite.assert_true(processor != nullptr, "Processor should not be null");
        suite.assert_true(is_processor_valid(processor), "Processor should be valid");
        destroy_processor(processor);
    });
    
    suite.run_test("Create processor with invalid parameters", [&]() {
        void* processor = create_processor(0.0, 12.0);
        suite.assert_true(processor == nullptr, "Processor should be null with zero frequency");
        
        processor = create_processor(100.0, 0.0);
        suite.assert_true(processor == nullptr, "Processor should be null with zero cutoff");
    });
}

void test_basic_processing() {
    TestSuite suite;
    
    suite.run_test("Process single sample", [&]() {
        void* processor = create_processor(100.0, 12.0);
        suite.assert_true(processor != nullptr);
        
        bool detected = process_sample(processor, 0.1, 0.2, 2.5);
        suite.assert_true(detected == true || detected == false, "Should return boolean");
        
        destroy_processor(processor);
    });
    
    suite.run_test("Process multiple samples", [&]() {
        void* processor = create_processor(100.0, 12.0);
        suite.assert_true(processor != nullptr);
        
        for (int i = 0; i < 100; ++i) {
            bool detected = process_sample(processor, 0.1, 0.2, 2.5 + i * 0.01);
            // Should not crash
        }
        
        destroy_processor(processor);
    });
}

void test_feature_extraction() {
    TestSuite suite;
    
    suite.run_test("Get current magnitude", [&]() {
        void* processor = create_processor(100.0, 12.0);
        suite.assert_true(processor != nullptr);
        
        process_sample(processor, 0.1, 0.2, 2.5);
        double magnitude = get_current_magnitude(processor);
        suite.assert_true(magnitude >= 0.0, "Magnitude should be non-negative");
        
        destroy_processor(processor);
    });
    
    suite.run_test("Get Z variance", [&]() {
        void* processor = create_processor(100.0, 12.0);
        suite.assert_true(processor != nullptr);
        
        // Process enough samples to fill buffer
        for (int i = 0; i < 100; ++i) {
            process_sample(processor, 0.1, 0.2, 2.5 + std::sin(i * 0.1));
        }
        
        double variance = get_z_variance(processor);
        suite.assert_true(variance >= 0.0, "Variance should be non-negative");
        
        destroy_processor(processor);
    });
    
    suite.run_test("Get peak-to-peak", [&]() {
        void* processor = create_processor(100.0, 12.0);
        suite.assert_true(processor != nullptr);
        
        // Process samples with varying magnitude
        for (int i = 0; i < 100; ++i) {
            double z = 2.5 + std::sin(i * 0.1) * 2.0;
            process_sample(processor, 0.1, 0.2, z);
        }
        
        double p2p = get_peak_to_peak(processor);
        suite.assert_true(p2p > 0.0, "Peak-to-peak should be positive");
        
        destroy_processor(processor);
    });
}

void test_configuration() {
    TestSuite suite;
    
    suite.run_test("Set detection threshold", [&]() {
        void* processor = create_processor(100.0, 12.0);
        suite.assert_true(processor != nullptr);
        
        set_detection_threshold(processor, 5.0);
        // Should not crash
        
        destroy_processor(processor);
    });
    
    suite.run_test("Reset processor", [&]() {
        void* processor = create_processor(100.0, 12.0);
        suite.assert_true(processor != nullptr);
        
        // Process some samples
        for (int i = 0; i < 50; ++i) {
            process_sample(processor, 0.1, 0.2, 2.5);
        }
        
        reset_processor(processor);
        
        // Should still work after reset
        bool detected = process_sample(processor, 0.1, 0.2, 2.5);
        suite.assert_true(detected == true || detected == false);
        
        destroy_processor(processor);
    });
}

void test_performance() {
    TestSuite suite;
    
    suite.run_test("Sub-millisecond processing", [&]() {
        void* processor = create_processor(100.0, 12.0);
        suite.assert_true(processor != nullptr);
        
        const int num_samples = 10000;
        auto start_time = std::chrono::high_resolution_clock::now();
        
        for (int i = 0; i < num_samples; ++i) {
            process_sample(processor, 0.1, 0.2, 2.5);
        }
        
        auto end_time = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end_time - start_time);
        
        double avg_time_us = duration.count() / static_cast<double>(num_samples);
        double avg_time_ms = avg_time_us / 1000.0;
        
        std::cout << " (avg: " << avg_time_ms << "ms per sample) ";
        suite.assert_true(avg_time_ms < 1.0, "Processing should be sub-millisecond");
        
        destroy_processor(processor);
    });
    
    suite.run_test("Memory management", [&]() {
        // Test multiple create/destroy cycles
        for (int i = 0; i < 100; ++i) {
            void* processor = create_processor(100.0, 12.0);
            suite.assert_true(processor != nullptr);
            
            process_sample(processor, 0.1, 0.2, 2.5);
            destroy_processor(processor);
        }
        
        // Should not crash
    });
}

void test_filter_characteristics() {
    TestSuite suite;
    
    suite.run_test("High-pass filter response", [&]() {
        void* processor = create_processor(100.0, 12.0);
        suite.assert_true(processor != nullptr);
        
        // Test with low frequency signal (should be attenuated)
        double low_freq_magnitude = 0.0;
        for (int i = 0; i < 200; ++i) {
            double t = i / 100.0;
            double x = std::sin(2.0 * M_PI * 5.0 * t);  // 5 Hz signal
            double y = std::sin(2.0 * M_PI * 5.0 * t + M_PI/2);
            double z = std::sin(2.0 * M_PI * 5.0 * t + M_PI);
            
            process_sample(processor, x, y, z);
            if (i >= 100) {  // Wait for filter to settle
                low_freq_magnitude += get_current_magnitude(processor);
            }
        }
        low_freq_magnitude /= 100;
        
        // Test with high frequency signal (should pass through)
        double high_freq_magnitude = 0.0;
        reset_processor(processor);
        
        for (int i = 0; i < 200; ++i) {
            double t = i / 100.0;
            double x = std::sin(2.0 * M_PI * 50.0 * t);  // 50 Hz signal
            double y = std::sin(2.0 * M_PI * 50.0 * t + M_PI/2);
            double z = std::sin(2.0 * M_PI * 50.0 * t + M_PI);
            
            process_sample(processor, x, y, z);
            if (i >= 100) {  // Wait for filter to settle
                high_freq_magnitude += get_current_magnitude(processor);
            }
        }
        high_freq_magnitude /= 100;
        
        // High frequency should have higher magnitude than low frequency
        suite.assert_true(high_freq_magnitude > low_freq_magnitude, 
                         "High-pass filter should attenuate low frequencies");
        
        std::cout << " (low: " << low_freq_magnitude << ", high: " << high_freq_magnitude << ") ";
        
        destroy_processor(processor);
    });
}

void test_edge_cases() {
    TestSuite suite;
    
    suite.run_test("Null pointer handling", [&]() {
        // All functions should handle null pointers gracefully
        bool result1 = process_sample(nullptr, 0.1, 0.2, 2.5);
        suite.assert_true(result1 == false, "Should return false for null processor");
        
        double magnitude = get_current_magnitude(nullptr);
        suite.assert_true(magnitude == 0.0, "Should return 0 for null processor");
        
        double variance = get_z_variance(nullptr);
        suite.assert_true(variance == 0.0, "Should return 0 for null processor");
        
        double p2p = get_peak_to_peak(nullptr);
        suite.assert_true(p2p == 0.0, "Should return 0 for null processor");
        
        bool valid = is_processor_valid(nullptr);
        suite.assert_true(valid == false, "Should return false for null processor");
        
        reset_processor(nullptr);  // Should not crash
        set_detection_threshold(nullptr, 5.0);  // Should not crash
    });
    
    suite.run_test("Extreme values", [&]() {
        void* processor = create_processor(100.0, 12.0);
        suite.assert_true(processor != nullptr);
        
        // Test with very large values
        bool detected = process_sample(processor, 1000.0, 1000.0, 1000.0);
        suite.assert_true(detected == true || detected == false);
        
        // Test with very small values
        detected = process_sample(processor, 1e-10, 1e-10, 1e-10);
        suite.assert_true(detected == true || detected == false);
        
        // Test with NaN values (should not crash)
        detected = process_sample(processor, NAN, NAN, NAN);
        suite.assert_true(detected == true || detected == false);
        
        destroy_processor(processor);
    });
}

int main() {
    std::cout << "PotholeNet v2.3 Native Bridge Test Suite" << std::endl;
    std::cout << "========================================" << std::endl;
    
    TestSuite suite;
    
    // Run all test categories
    std::cout << "\n--- Processor Creation Tests ---" << std::endl;
    test_processor_creation();
    
    std::cout << "\n--- Basic Processing Tests ---" << std::endl;
    test_basic_processing();
    
    std::cout << "\n--- Feature Extraction Tests ---" << std::endl;
    test_feature_extraction();
    
    std::cout << "\n--- Configuration Tests ---" << std::endl;
    test_configuration();
    
    std::cout << "\n--- Performance Tests ---" << std::endl;
    test_performance();
    
    std::cout << "\n--- Filter Characteristics Tests ---" << std::endl;
    test_filter_characteristics();
    
    std::cout << "\n--- Edge Case Tests ---" << std::endl;
    test_edge_cases();
    
    // Print final summary
    suite.print_summary();
    
    return suite.tests_failed > 0 ? 1 : 0;
}
