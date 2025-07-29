#!/bin/bash

# run_tests.sh - Comprehensive testing script for the CS New Grad Job Scraper
# This script tests multiple companies to validate configurations and performance

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Emoji for better visual feedback
SUCCESS="✅"
FAILURE="❌"
WARNING="⚠️"
INFO="ℹ️"
ROCKET="🚀"
CLOCK="🕐"
CHART="📊"

# Function to print colored output
print_color() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to print section headers
print_header() {
    local title=$1
    echo ""
    echo "$(print_color $BLUE "==========================================")"
    echo "$(print_color $CYAN "$title")"
    echo "$(print_color $BLUE "==========================================")"
}

# Function to print subsection headers
print_section() {
    local title=$1
    echo ""
    echo "$(print_color $PURPLE "--- $title ---")"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check prerequisites
check_prerequisites() {
    print_header "${ROCKET} CHECKING PREREQUISITES"
    
    local all_good=true
    
    # Check Python 3
    if command_exists python3; then
        local python_version=$(python3 --version 2>&1)
        print_color $GREEN "${SUCCESS} Python found: $python_version"
    else
        print_color $RED "${FAILURE} Python 3 not found. Please install Python 3.8+"
        all_good=false
    fi
    
    # Check if required files exist
    local required_files=("scraper.py" "companies_config.json" "requirements.txt")
    
    for file in "${required_files[@]}"; do
        if [[ -f "$file" ]]; then
            print_color $GREEN "${SUCCESS} Found: $file"
        else
            print_color $RED "${FAILURE} Missing required file: $file"
            all_good=false
        fi
    done
    
    # Check if virtual environment is activated
    if [[ -n "$VIRTUAL_ENV" ]]; then
        print_color $GREEN "${SUCCESS} Virtual environment active: $VIRTUAL_ENV"
    else
        print_color $YELLOW "${WARNING} No virtual environment detected (recommended but not required)"
    fi
    
    # Try to import required packages
    print_section "Checking Python Dependencies"
    
    local packages=("requests" "selenium" "pandas" "beautifulsoup4")
    
    for package in "${packages[@]}"; do
        if python3 -c "import $package" 2>/dev/null; then
            print_color $GREEN "${SUCCESS} $package installed"
        else
            print_color $RED "${FAILURE} $package not installed"
            all_good=false
        fi
    done
    
    if [[ "$all_good" == false ]]; then
        echo ""
        print_color $RED "${FAILURE} Prerequisites check failed. Please install missing dependencies:"
        echo "  pip install -r requirements.txt"
        exit 1
    fi
    
    print_color $GREEN "${SUCCESS} All prerequisites satisfied!"
}

# Function to test a single company
test_company() {
    local company=$1
    local start_time=$(date +%s)
    
    print_section "${ROCKET} Testing $company"
    
    # Run the test
    if python3 scraper.py --test-company "$company" --no-email > /tmp/test_${company}.log 2>&1; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        # Extract job count from log
        local job_count=$(grep -o "Jobs found: [0-9]*" /tmp/test_${company}.log | grep -o "[0-9]*" || echo "0")
        
        print_color $GREEN "${SUCCESS} $company: $job_count jobs found (${duration}s)"
        
        # Store results
        echo "$company,$job_count,$duration,SUCCESS" >> test_results.csv
        
        return 0
    else
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        print_color $RED "${FAILURE} $company: Test failed (${duration}s)"
        
        # Show error details
        if [[ -f "/tmp/test_${company}.log" ]]; then
            echo "   Error details:"
            tail -3 /tmp/test_${company}.log | sed 's/^/   /'
        fi
        
        # Store results
        echo "$company,0,$duration,FAILED" >> test_results.csv
        
        return 1
    fi
}

# Function to run quick tests on priority companies
run_quick_tests() {
    print_header "${CLOCK} QUICK TESTS (Top 10 Companies)"
    
    # Priority companies (most important to test)
    local priority_companies=(
        "Microsoft"
        "Google" 
        "Amazon"
        "Meta"
        "Apple"
        "Netflix"
        "Tesla"
        "Salesforce"
        "Adobe"
        "Oracle"
    )
    
    local successful=0
    local total=${#priority_companies[@]}
    
    # Initialize results file
    echo "Company,Jobs Found,Duration (s),Status" > test_results.csv
    
    for company in "${priority_companies[@]}"; do
        if test_company "$company"; then
            ((successful++))
        fi
        
        # Add delay between tests to be respectful
        sleep 2
    done
    
    print_section "${CHART} Quick Test Summary"
    print_color $CYAN "Tested: $total companies"
    print_color $GREEN "Successful: $successful"
    print_color $RED "Failed: $((total - successful))"
    
    local success_rate=$((successful * 100 / total))
    if [[ $success_rate -ge 80 ]]; then
        print_color $GREEN "${SUCCESS} Success rate: ${success_rate}% (Excellent!)"
    elif [[ $success_rate -ge 60 ]]; then
        print_color $YELLOW "${WARNING} Success rate: ${success_rate}% (Good)"
    else
        print_color $RED "${FAILURE} Success rate: ${success_rate}% (Needs attention)"
    fi
}

# Function to run comprehensive tests
run_comprehensive_tests() {
    print_header "${ROCKET} COMPREHENSIVE TESTS (All Companies)"
    
    # Get all companies from config file
    local all_companies=($(python3 -c "
import json
with open('companies_config.json', 'r') as f:
    config = json.load(f)
for company in config.keys():
    if config[company].get('enabled', True):
        print(company)
" 2>/dev/null))
    
    if [[ ${#all_companies[@]} -eq 0 ]]; then
        print_color $RED "${FAILURE} Could not load companies from config file"
        return 1
    fi
    
    print_color $CYAN "${INFO} Found ${#all_companies[@]} enabled companies"
    
    local successful=0
    local total=${#all_companies[@]}
    
    # Initialize results file
    echo "Company,Jobs Found,Duration (s),Status" > test_results_comprehensive.csv
    
    for company in "${all_companies[@]}"; do
        if test_company "$company"; then
            ((successful++))
        fi
        
        # Progress indicator
        local progress=$((successful * 100 / total))
        print_color $CYAN "${INFO} Progress: ${progress}% ($successful/$total completed)"
        
        # Add delay between tests
        sleep 3
    done
    
    print_section "${CHART} Comprehensive Test Summary"
    print_color $CYAN "Total companies tested: $total"
    print_color $GREEN "Successful: $successful"
    print_color $RED "Failed: $((total - successful))"
    
    # Generate detailed report
    generate_test_report "test_results_comprehensive.csv"
}

# Function to test filtering accuracy
test_filtering() {
    print_header "${CLOCK} TESTING CS + NEW GRAD FILTERING"
    
    print_color $CYAN "${INFO} Testing job title filtering accuracy..."
    
    # Run filtering test
    if python3 -c "
from scraper import EnhancedJobScraper
scraper = EnhancedJobScraper()

test_cases = [
    ('Software Engineer - New Grad', True),
    ('Senior Software Engineer', False),
    ('Data Scientist - Recent Graduate', True),
    ('Marketing Manager - Entry Level', False),
    ('Backend Developer - Junior', True),
    ('Software Engineering Intern', False),
    ('Machine Learning Engineer - University Hire', True),
    ('Product Manager - New Grad', True),
    ('Sales Representative', False),
    ('DevOps Engineer - Entry Level', True)
]

correct = 0
total = len(test_cases)

print('Testing CS + New Grad filtering:')
for title, expected in test_cases:
    result = scraper.is_relevant_job(title)
    status = '✅' if result == expected else '❌'
    print(f'  {status} \"{title}\" -> {result} (expected: {expected})')
    if result == expected:
        correct += 1

accuracy = (correct / total) * 100
print(f'\\nFiltering Accuracy: {correct}/{total} ({accuracy:.1f}%)')

scraper.cleanup()
" 2>/dev/null; then
        print_color $GREEN "${SUCCESS} Filtering test completed"
    else
        print_color $RED "${FAILURE} Filtering test failed"
    fi
}

# Function to test Selenium setup
test_selenium() {
    print_header "${ROCKET} TESTING SELENIUM SETUP"
    
    print_color $CYAN "${INFO} Testing Chrome driver and Selenium functionality..."
    
    # Test Selenium
    if python3 -c "
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

try:
    print('Setting up Chrome driver...')
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    driver = webdriver.Chrome(options=chrome_options)
    print('✅ Chrome driver initialized successfully')
    
    print('Testing basic navigation...')
    driver.get('https://www.google.com')
    print(f'✅ Successfully loaded: {driver.title}')
    
    driver.quit()
    print('✅ Selenium test completed successfully')
    
except Exception as e:
    print(f'❌ Selenium test failed: {e}')
    exit(1)
" 2>/dev/null; then
        print_color $GREEN "${SUCCESS} Selenium is working correctly"
    else
        print_color $RED "${FAILURE} Selenium test failed"
        echo ""
        print_color $YELLOW "${WARNING} Possible solutions:"
        echo "  • Install Chrome: sudo apt-get install google-chrome-stable"
        echo "  • Install ChromeDriver: pip install webdriver-manager"
        echo "  • Check Chrome version compatibility"
    fi
}

# Function to generate test report
generate_test_report() {
    local results_file=$1
    
    if [[ ! -f "$results_file" ]]; then
        return 1
    fi
    
    print_section "${CHART} Generating Test Report"
    
    # Create HTML report
    local report_file="test_report_$(date +%Y%m%d_%H%M%S).html"
    
    cat > "$report_file" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>CS New Grad Job Scraper - Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #f0f0f0; padding: 20px; border-radius: 5px; }
        .success { color: green; }
        .failure { color: red; }
        .warning { color: orange; }
        table { border-collapse: collapse; width: 100%; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .stats { display: flex; gap: 20px; margin: 20px 0; }
        .stat-box { background: #f9f9f9; padding: 15px; border-radius: 5px; flex: 1; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🎓 CS New Grad Job Scraper - Test Report</h1>
        <p>Generated: $(date)</p>
    </div>
    
    <div class="stats">
        <div class="stat-box">
            <h3>📊 Statistics</h3>
            <p>Total Companies: $(tail -n +2 "$results_file" | wc -l)</p>
            <p class="success">Successful: $(grep "SUCCESS" "$results_file" | wc -l)</p>
            <p class="failure">Failed: $(grep "FAILED" "$results_file" | wc -l)</p>
        </div>
        <div class="stat-box">
            <h3>🎯 Top Performers</h3>
EOF

    # Add top performers
    tail -n +2 "$results_file" | sort -t',' -k2 -nr | head -5 | while IFS=',' read company jobs duration status; do
        if [[ "$status" == "SUCCESS" ]]; then
            echo "            <p class=\"success\">$company: $jobs jobs</p>" >> "$report_file"
        fi
    done
    
    cat >> "$report_file" << EOF
        </div>
    </div>
    
    <h2>📋 Detailed Results</h2>
    <table>
        <tr>
            <th>Company</th>
            <th>Jobs Found</th>
            <th>Duration (s)</th>
            <th>Status</th>
        </tr>
EOF

    # Add detailed results
    tail -n +2 "$results_file" | while IFS=',' read company jobs duration status; do
        local status_class="success"
        if [[ "$status" == "FAILED" ]]; then
            status_class="failure"
        fi
        echo "        <tr><td>$company</td><td>$jobs</td><td>$duration</td><td class=\"$status_class\">$status</td></tr>" >> "$report_file"
    done
    
    cat >> "$report_file" << EOF
    </table>
</body>
</html>
EOF

    print_color $GREEN "${SUCCESS} Test report generated: $report_file"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --quick         Run quick tests (top 10 companies)"
    echo "  --comprehensive Run comprehensive tests (all companies)"
    echo "  --filtering     Test CS + New Grad filtering only"
    echo "  --selenium      Test Selenium setup only"
    echo "  --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --quick                    # Quick test of priority companies"
    echo "  $0 --comprehensive           # Test all enabled companies"
    echo "  $0 --filtering --selenium    # Test specific components"
    echo ""
    echo "Default (no options): Run prerequisites check + quick tests"
}

# Main function
main() {
    local run_quick=false
    local run_comprehensive=false
    local run_filtering=false
    local run_selenium=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --quick)
                run_quick=true
                shift
                ;;
            --comprehensive)
                run_comprehensive=true
                shift
                ;;
            --filtering)
                run_filtering=true
                shift
                ;;
            --selenium)
                run_selenium=true
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # If no specific tests requested, run default sequence
    if [[ "$run_quick" == false && "$run_comprehensive" == false && "$run_filtering" == false && "$run_selenium" == false ]]; then
        run_quick=true
        run_filtering=true
        run_selenium=true
    fi
    
    # Always check prerequisites first
    check_prerequisites
    
    # Run requested tests
    if [[ "$run_selenium" == true ]]; then
        test_selenium
    fi
    
    if [[ "$run_filtering" == true ]]; then
        test_filtering
    fi
    
    if [[ "$run_quick" == true ]]; then
        run_quick_tests
    fi
    
    if [[ "$run_comprehensive" == true ]]; then
        run_comprehensive_tests
    fi
    
    # Final summary
    print_header "${SUCCESS} TESTING COMPLETED"
    
    if [[ -f "test_results.csv" ]]; then
        local total_jobs=$(tail -n +2 test_results.csv | cut -d',' -f2 | awk '{sum += $1} END {print sum}')
        local successful_companies=$(grep "SUCCESS" test_results.csv | wc -l)
        
        print_color $CYAN "${CHART} Final Summary:"
        print_color $GREEN "  • Total CS jobs found: $total_jobs"
        print_color $GREEN "  • Successful companies: $successful_companies"
        print_color $CYAN "  • Results saved to: test_results.csv"
        
        if [[ -f "test_report_"*.html ]]; then
            local report_file=$(ls -t test_report_*.html | head -1)
            print_color $CYAN "  • HTML report: $report_file"
        fi
    fi
    
    print_color $GREEN "${SUCCESS} All tests completed successfully!"
    
    # Cleanup temp files
    rm -f /tmp/test_*.log
}

# Make sure script is executable
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi