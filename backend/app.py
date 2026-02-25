import tempfile
import shutil
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
import sys
from werkzeug.utils import secure_filename

# Add current directory to path to ensure we can import utils.py
sys.path.insert(0, os.path.dirname(__file__))

from logic import ExamProcessor
import utils as utils_module

# Import specific functions with error handling
try:
    validate_file_extension = utils_module.validate_file_extension
    sanitize_filename = utils_module.sanitize_filename
    format_response = utils_module.format_response
    validate_excel_file = utils_module.validate_excel_file
    check_file_size = utils_module.check_file_size
    validate_year_input = utils_module.validate_year_input
    log_error = utils_module.log_error
except AttributeError as e:
    print(f"Error importing from utils: {e}")
    # Define fallback functions
    def validate_file_extension(filename, allowed_extensions):
        if not filename or '.' not in filename:
            return False
        extension = filename.rsplit('.', 1)[1].lower()
        return extension in allowed_extensions
    
    def sanitize_filename(filename):
        import re
        if not filename:
            return "unknown_file"
        sanitized = re.sub(r'[^\w\s.-]', '', filename).strip()
        sanitized = re.sub(r'\s+', '_', sanitized)
        return sanitized if sanitized else "unknown_file"
    
    def format_response(success, message, data=None):
        response = {'success': success, 'message': message}
        if data:
            response['data'] = data
        return response
    
    def validate_excel_file(file_path):
        return True, "File validation skipped"
    
    def check_file_size(file_path, max_size_mb=16):
        return True, "Size check skipped"
    
    def validate_year_input(year_str):
        valid_years = ['I', 'II', 'III', '1', '2', '3']
        return year_str in valid_years, "Year validation"
    
    def log_error(msg, exception=None):
        print(f"ERROR: {msg}")
        if exception:
            print(f"Exception: {exception}")

app = Flask(__name__, 
           template_folder=os.path.join(os.path.dirname(__file__), '..', 'frontend', 'templates'),
           static_folder=os.path.join(os.path.dirname(__file__), '..', 'frontend', 'static'))
CORS(app)  # Enable CORS for all routes

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

# Use temporary directory for Vercel
UPLOAD_FOLDER = tempfile.mkdtemp()
OUTPUT_FOLDER = tempfile.mkdtemp()

@app.route('/')
def home():
    """Render the frontend index.html"""
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_files():
    """
    Process FCTC and Roll Call Excel files
    Accepts: FCTC file, Roll Call file, Year
    Returns: Success message and file paths
    """
    try:
        
        # Check if files are present in request
        if 'fctc_file' not in request.files or 'roll_call_file' not in request.files:
            log_error("Missing files in request")
            return jsonify(format_response(
                False, 
                "Both FCTC file and Roll Call file are required"
            )), 400
        
        fctc_file = request.files['fctc_file']
        roll_call_file = request.files['roll_call_file']
        year = request.form.get('year', '').strip()
        
        # Validate files are selected
        if not fctc_file or fctc_file.filename == '':
            return jsonify(format_response(
                False, 
                "Please select the FCTC Excel file"
            )), 400
            
        if not roll_call_file or roll_call_file.filename == '':
            return jsonify(format_response(
                False, 
                "Please select the Roll Call Excel file"
            )), 400
        
        # Validate year input
        year_valid, year_message = validate_year_input(year)
        if not year_valid:
            return jsonify(format_response(False, year_message)), 400
        
        # Validate file extensions
        if not validate_file_extension(fctc_file.filename, ALLOWED_EXTENSIONS):
            return jsonify(format_response(
                False, 
                f"FCTC file must be an Excel file. Allowed formats: {', '.join(ALLOWED_EXTENSIONS)}"
            )), 400
            
        if not validate_file_extension(roll_call_file.filename, ALLOWED_EXTENSIONS):
            return jsonify(format_response(
                False, 
                f"Roll Call file must be an Excel file. Allowed formats: {', '.join(ALLOWED_EXTENSIONS)}"
            )), 400
        
        # Save uploaded files with validation
        import time
        timestamp = str(int(time.time()))
        
        fctc_filename = secure_filename(sanitize_filename(fctc_file.filename))
        roll_call_filename = secure_filename(sanitize_filename(roll_call_file.filename))
        
        # Add timestamp to avoid conflicts
        fctc_filename = f"{timestamp}_fctc_{fctc_filename}"
        roll_call_filename = f"{timestamp}_rollcall_{roll_call_filename}"
        
        fctc_path = os.path.join(UPLOAD_FOLDER, fctc_filename)
        roll_call_path = os.path.join(UPLOAD_FOLDER, roll_call_filename)
        
        # Save files
        try:
            fctc_file.save(fctc_path)
            roll_call_file.save(roll_call_path)
        except Exception as e:
            log_error("Error saving uploaded files", e)
            return jsonify(format_response(
                False, 
                "Error saving uploaded files. Please try again."
            )), 500
        
        # Validate saved files
        fctc_size_valid, fctc_size_msg = check_file_size(fctc_path)
        if not fctc_size_valid:
            os.remove(fctc_path) if os.path.exists(fctc_path) else None
            os.remove(roll_call_path) if os.path.exists(roll_call_path) else None
            return jsonify(format_response(False, f"FCTC file error: {fctc_size_msg}")), 400
        
        roll_call_size_valid, roll_call_size_msg = check_file_size(roll_call_path)
        if not roll_call_size_valid:
            os.remove(fctc_path) if os.path.exists(fctc_path) else None
            os.remove(roll_call_path) if os.path.exists(roll_call_path) else None
            return jsonify(format_response(False, f"Roll Call file error: {roll_call_size_msg}")), 400
        
        # Validate Excel files can be read
        fctc_valid, fctc_msg = validate_excel_file(fctc_path)
        if not fctc_valid:
            os.remove(fctc_path) if os.path.exists(fctc_path) else None
            os.remove(roll_call_path) if os.path.exists(roll_call_path) else None
            return jsonify(format_response(False, f"FCTC file error: {fctc_msg}")), 400
        
        roll_call_valid, roll_call_msg = validate_excel_file(roll_call_path)
        if not roll_call_valid:
            os.remove(fctc_path) if os.path.exists(fctc_path) else None
            os.remove(roll_call_path) if os.path.exists(roll_call_path) else None
            return jsonify(format_response(False, f"Roll Call file error: {roll_call_msg}")), 400
        
        # Process files using ExamProcessor
        processor = ExamProcessor()
        
        # Convert year to appropriate format
        year_mapping = {'I': 1, 'II': 2, 'III': 3, '1': 1, '2': 2, '3': 3}
        year_int = year_mapping.get(year, 1)
        
        # Process files using new PRN-first pipeline
        try:
            result = processor.process_and_generate_reports(fctc_path, roll_call_path, year_int)
        except Exception as e:
            # For now, all errors are treated as real errors
            raise e
        
        # Clean up uploaded files (optional - comment out if you want to keep them)
        try:
            os.remove(fctc_path)
            os.remove(roll_call_path)
        except:
            pass  # Ignore cleanup errors
        
        # Prepare response with downloadable division-wise data
        division_reports = result.get('division_reports', {})
        download_data = {}
        
        # Generate CSV for each division
        for division, report_data in division_reports.items():
            csv_content = _generate_csv_content(report_data['students'])
            safe_division_name = division.replace('/', '_').replace('\\', '_').replace(' ', '_')
            download_data[f'division_{safe_division_name}'] = {
                'csv_content': csv_content,
                'filename': f'attendance_report_division_{safe_division_name}.csv',
                'total_students': report_data['total_students'],
                'present_count': report_data['present_count'],
                'absent_count': report_data['absent_count']
            }
        
        response_data = {
            'matched_students': result.get('matched_students', 0),
            'generated_files': result.get('reports', {}).get('files_created', []),
            'year': year,
            'summary': result.get('reports', {}).get('summary', ''),
            'divisions': result.get('divisions', []),
            'division_count': result.get('division_count', 0),
            'division_reports': division_reports,
            'download_data': download_data
        }
        
        return jsonify(format_response(
            True,
            "PRN-first VIT matching pipeline completed successfully",
            response_data
        )), 200
        
    except Exception as e:
        # Clean up files on error
        try:
            if 'fctc_path' in locals() and os.path.exists(fctc_path):
                os.remove(fctc_path)
            if 'roll_call_path' in locals() and os.path.exists(roll_call_path):
                os.remove(roll_call_path)
        except:
            pass
        
        log_error("Error processing files", e)
        return jsonify(format_response(
            False, 
            f"Error processing files: {str(e)}"
        )), 500

def _generate_csv_content(attendance_data):
    """Generate CSV content from attendance data"""
    if not attendance_data:
        return ""
    
    import io
    import csv
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=attendance_data[0].keys())
    writer.writeheader()
    writer.writerows(attendance_data)
    
    return output.getvalue()

@app.route('/debug-prn', methods=['POST'])
def debug_prn_matching():
    """
    Debug endpoint to analyze PRN matching issues
    """
    try:
        # Check if files are present in request
        if 'fctc_file' not in request.files or 'roll_call_file' not in request.files:
            return jsonify(format_response(
                False, 
                "Both FCTC file and Roll Call file are required for debugging"
            )), 400
        
        fctc_file = request.files['fctc_file']
        roll_call_file = request.files['roll_call_file']
        
        # Validate files are selected
        if not fctc_file or fctc_file.filename == '':
            return jsonify(format_response(False, "Please select the FCTC Excel file")), 400
            
        if not roll_call_file or roll_call_file.filename == '':
            return jsonify(format_response(False, "Please select the Roll Call Excel file")), 400
        
        # Save files temporarily for debugging
        import time
        timestamp = str(int(time.time()))
        
        fctc_filename = f"{timestamp}_debug_fctc_{secure_filename(fctc_file.filename)}"
        roll_call_filename = f"{timestamp}_debug_rollcall_{secure_filename(roll_call_file.filename)}"
        
        fctc_path = os.path.join(UPLOAD_FOLDER, fctc_filename)
        roll_call_path = os.path.join(UPLOAD_FOLDER, roll_call_filename)
        
        fctc_file.save(fctc_path)
        roll_call_file.save(roll_call_path)
        
        # Debug analysis
        processor = ExamProcessor()
        debug_info = {}
        
        try:
            # Read and analyze FCTC file using openpyxl
            data_rows, headers = processor._read_excel_with_header_detection(fctc_path)
            debug_info['fctc_columns'] = headers
            debug_info['fctc_row_count'] = len(data_rows)
            
            # Try to extract FCTC data
            fctc_data = processor._extract_fctc_data(data_rows, headers)
            debug_info['fctc_extracted_count'] = len(fctc_data)
            debug_info['fctc_sample_prns'] = [record['PRN_CLEAN'] for record in fctc_data[:5]]
            
        except Exception as e:
            debug_info['fctc_error'] = str(e)
        
        try:
            # Read and analyze Roll Call file using openpyxl
            data_rows, headers = processor._read_excel_with_header_detection(roll_call_path)
            debug_info['roll_call_columns'] = headers
            debug_info['roll_call_row_count'] = len(data_rows)
            
            # Try to extract Roll Call data
            roll_call_data = processor._extract_roll_call_data(data_rows, headers)
            debug_info['roll_call_extracted_count'] = len(roll_call_data)
            debug_info['roll_call_sample_prns'] = [record['PRN_CLEAN'] for record in roll_call_data[:5]]
            
        except Exception as e:
            debug_info['roll_call_error'] = str(e)
        
        # Compare PRNs if both extractions succeeded
        if 'fctc_sample_prns' in debug_info and 'roll_call_sample_prns' in debug_info:
            fctc_prns = {record['PRN_CLEAN'] for record in fctc_data}
            roll_call_prns = {record['PRN_CLEAN'] for record in roll_call_data}
            matches = fctc_prns.intersection(roll_call_prns)
            
            debug_info['fctc_unique_prns'] = len(fctc_prns)
            debug_info['roll_call_unique_prns'] = len(roll_call_prns)
            debug_info['matching_prns'] = len(matches)
            debug_info['sample_matches'] = list(matches)[:5] if matches else []
            
            # Character-level analysis of first PRNs
            if fctc_prns and roll_call_prns:
                fctc_first = list(fctc_prns)[0]
                roll_first = list(roll_call_prns)[0]
                debug_info['character_analysis'] = {
                    'fctc_first_prn': fctc_first,
                    'roll_call_first_prn': roll_first,
                    'fctc_length': len(fctc_first),
                    'roll_call_length': len(roll_first),
                    'fctc_chars': [ord(c) for c in fctc_first],
                    'roll_call_chars': [ord(c) for c in roll_first]
                }
        
        # Clean up debug files
        try:
            os.remove(fctc_path)
            os.remove(roll_call_path)
        except:
            pass
        
        return jsonify(format_response(True, "Debug analysis completed", debug_info)), 200
        
    except Exception as e:
        log_error("Error in PRN debug analysis", e)
        return jsonify(format_response(False, f"Debug error: {str(e)}")), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify(format_response(
        True,
        "FCTC Automation Backend Running"
    )), 200
@app.route('/download/<path:filename>')
def download_file(filename):
    """Download generated report files - Vercel compatible"""
    from flask import Response
    try:
        # Since this is serverless, we need to get the data from the session or request
        # For now, return instructions on how to download
        return jsonify(format_response(
            True,
            "Download data is included in the processing response. Use the 'download_data' field to get CSV or JSON content.",
            {
                "instructions": [
                    "1. The processed data is returned directly in the API response",
                    "2. Look for 'download_data' in the response",
                    "3. Use 'attendance_report_csv' for CSV format",
                    "4. Use 'attendance_report_json' for JSON format",
                    "5. Copy the content and save as a file on your computer"
                ]
            }
        )), 200
            
    except Exception as e:
        print(f"✗ Error in download route: {e}")
        return jsonify(format_response(
            False,
            f"Error downloading file: {str(e)}"
        )), 500

@app.route('/download-csv', methods=['POST'])
def download_csv():
    """Generate and return CSV file content"""
    from flask import Response
    try:
        data = request.get_json()
        if not data or 'attendance_report' not in data:
            return jsonify(format_response(
                False,
                "No attendance report data provided"
            )), 400
        
        csv_content = _generate_csv_content(data['attendance_report'])
        
        return Response(
            csv_content,
            mimetype='text/csv',
            headers={
                'Content-Disposition': 'attachment; filename=attendance_report.csv',
                'Content-Type': 'text/csv'
            }
        )
        
    except Exception as e:
        return jsonify(format_response(
            False,
            f"Error generating CSV: {str(e)}"
        )), 500

@app.errorhandler(413)
def too_large(e):
    """Handle file too large error"""
    return jsonify(format_response(
        False,
        "File too large. Maximum size is 16MB."
    )), 413

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return jsonify(format_response(
        False,
        "Endpoint not found"
    )), 404

@app.errorhandler(500)
def internal_error(e):
    """Handle internal server errors"""
    return jsonify(format_response(
        False,
        "Internal server error"
    )), 500

if __name__ == '__main__':
    # Disable reloader to prevent constant restarts
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)