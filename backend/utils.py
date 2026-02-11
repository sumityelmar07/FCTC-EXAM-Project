# Helper functions and utilities
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_file_extension(filename, allowed_extensions):
    """Validate if file has allowed extension"""
    if not filename or '.' not in filename:
        return False
    extension = filename.rsplit('.', 1)[1].lower()
    return extension in allowed_extensions

def validate_excel_file(file_path):
    """Validate Excel file exists and is readable"""
    try:
        import openpyxl
        
        if not os.path.exists(file_path):
            raise ValueError(f"File does not exist: {file_path}")
        
        if os.path.getsize(file_path) == 0:
            raise ValueError("File is empty")
        
        # Try to read the file to ensure it's a valid Excel file
        workbook = openpyxl.load_workbook(file_path, data_only=True)
        sheet = workbook.active
        
        # Check if there's any data
        has_data = False
        for row in sheet.iter_rows(max_row=10, values_only=True):
            if any(cell is not None for cell in row):
                has_data = True
                break
        
        workbook.close()
        
        if not has_data:
            raise ValueError("Excel file contains no data")
        
        return True, "File is valid"
        
    except Exception as e:
        logger.error(f"Excel file validation failed for {file_path}: {str(e)}")
        return False, f"Invalid Excel file: {str(e)}"

def validate_required_columns(df, required_columns, file_type="file"):
    """Validate that DataFrame contains required columns"""
    if df is None or df.empty:
        return False, f"{file_type} is empty"
    
    # Strip spaces from column names for comparison
    df_columns = [col.strip() for col in df.columns]
    missing_columns = []
    
    for req_col in required_columns:
        # Check for exact match or common variations
        found = False
        for df_col in df_columns:
            if (df_col.lower() == req_col.lower() or 
                df_col.lower().replace(' ', '') == req_col.lower().replace(' ', '') or
                df_col.lower().replace('_', '') == req_col.lower().replace('_', '')):
                found = True
                break
        
        if not found:
            missing_columns.append(req_col)
    
    if missing_columns:
        return False, f"Missing required columns in {file_type}: {', '.join(missing_columns)}"
    
    return True, "All required columns found"

def get_fctc_required_columns():
    """Get list of required columns for FCTC file"""
    return ['PRN', 'Roll', 'Name', 'Marks']  # Common required columns

def get_roll_call_required_columns():
    """Get list of required columns for Roll Call file"""
    return ['PRN', 'Roll', 'Name', 'Division']  # Common required columns

def sanitize_filename(filename):
    """Sanitize filename for safe storage"""
    import re
    if not filename:
        return "unknown_file"
    
    # Remove path separators and dangerous characters
    sanitized = re.sub(r'[^\w\s.-]', '', filename).strip()
    # Replace spaces with underscores
    sanitized = re.sub(r'\s+', '_', sanitized)
    # Ensure it's not empty
    if not sanitized:
        sanitized = "unknown_file"
    
    return sanitized

def format_response(success, message, data=None):
    """Format API response consistently"""
    response = {
        'success': success,
        'message': message
    }
    if data:
        response['data'] = data
    return response

def log_error(error_msg, exception=None):
    """Log error with optional exception details"""
    if exception:
        logger.error(f"{error_msg}: {str(exception)}", exc_info=True)
    else:
        logger.error(error_msg)

def validate_year_input(year_str):
    """Validate year input"""
    if not year_str or not year_str.strip():
        return False, "Year is required"
    
    year_str = year_str.strip()
    valid_years = ['I', 'II', 'III', '1', '2', '3']
    
    if year_str not in valid_years:
        return False, f"Invalid year. Must be one of: {', '.join(valid_years[:3])}"
    
    return True, "Year is valid"

def check_file_size(file_path, max_size_mb=16):
    """Check if file size is within limits"""
    try:
        if not os.path.exists(file_path):
            return False, "File does not exist"
        
        file_size = os.path.getsize(file_path)
        max_size_bytes = max_size_mb * 1024 * 1024
        
        if file_size > max_size_bytes:
            return False, f"File size ({file_size / (1024*1024):.1f}MB) exceeds limit of {max_size_mb}MB"
        
        if file_size == 0:
            return False, "File is empty"
        
        return True, "File size is acceptable"
        
    except Exception as e:
        return False, f"Error checking file size: {str(e)}"