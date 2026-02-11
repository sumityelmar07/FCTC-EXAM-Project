# Business logic for FCTC exam automation - PRN-FIRST PIPELINE ONLY
import openpyxl
import os
import re
from typing import Dict, List, Tuple, Optional

class ExamProcessor:
    """
    PRN-FIRST PIPELINE - EXTRACTS ONLY REQUIRED FIELDS FROM FCTC:
    
    SATAKAM (FCTC) FILE - REQUIRED FIELDS (extracts only these, ignores all others):
    - "Timestamp"
    - "Email Address"
    - "Score" (Total score)
    - "Full name- MANDATORY FOR ALL COLLEGE STUDENTS"
    - "College Name-MANDATORY FOR ALL COLLEGE STUDENTS ( Please select your specific college name carefully and accurately )"
    - "Year-MANDATORY FOR ALL COLLEGE STUDENTS"
    - "Roll Number-MANDATORY FOR ALL COLLEGE STUDENTS"
    - "Branch-MANDATORY ONLY FOR NON-VISHWAKARMA INSTITUTE OF TECHNOLOGY STUDENTS"
    - "Division-MANDATORY ONLY FOR NON-VISHWAKARMA INSTITUTE OF TECHNOLOGY STUDENTS"
    - "PRN - MANDATORY ONLY FOR VISHWAKARMA INSTITUTE OF TECHNOLOGY STUDENTS" (CRITICAL)
    - "Branch-Division- MANDATORY ONLY FOR VISHWAKARMA INSTITUTE OF TECHNOLOGY STUDENTS"
    
    ROLL CALL FILE - REQUIRED EXACT COLUMNS:
    - "PRN"
    - "Roll No" 
    - "Name"
    - "Division"
    (All other columns safely ignored)
    
    RULES:
    1. PRN is the primary and authoritative identifier
    2. Roll No is NOT used for matching (included for reference only)
    3. Division comes ONLY from Roll Call file
    4. FCTC file: Extract ONLY required fields, ignore all other columns
    5. Attendance logic: If PRN exists in FCTC → Present, Else → Absent
    6. Missing critical columns (PRN, Score) = ABORT with clear error
    7. Missing optional fields = Continue processing with available fields
    """
    
    def __init__(self):
        pass
    
    def _read_excel_with_header_detection(self, file_path: str) -> Tuple[List[List], List[str]]:
        """
        Read Excel file and detect header row automatically
        Returns: (data_rows, header_row)
        """
        try:
            workbook = openpyxl.load_workbook(file_path, data_only=True)
            sheet = workbook.active
            
            # Get all rows as lists
            all_rows = []
            for row in sheet.iter_rows(values_only=True):
                if any(cell is not None for cell in row):  # Skip completely empty rows
                    all_rows.append(list(row))
            
            if not all_rows:
                raise Exception("Excel file is empty")
            
            # Find header row (look for row with most non-empty string values)
            header_row_idx = 0
            max_string_count = 0
            
            for i, row in enumerate(all_rows[:10]):  # Check first 10 rows
                string_count = sum(1 for cell in row if isinstance(cell, str) and cell.strip())
                if string_count > max_string_count:
                    max_string_count = string_count
                    header_row_idx = i
            
            headers = [str(cell).strip() if cell is not None else "" for cell in all_rows[header_row_idx]]
            data_rows = all_rows[header_row_idx + 1:]
            
            workbook.close()
            return data_rows, headers
            
        except Exception as e:
            raise Exception(f"Error reading Excel file: {str(e)}")
    
    def _clean_prn(self, prn_value) -> str:
        """Clean and standardize PRN format"""
        if prn_value is None:
            return ""
        
        prn_str = str(prn_value).strip().upper()
        # Remove decimal points (Excel formatting)
        prn_str = re.sub(r'\.0+$', '', prn_str)
        # Remove any non-alphanumeric characters except common separators
        prn_clean = re.sub(r'[^\w\-]', '', prn_str)
        
        # Filter out invalid values
        if prn_clean in ['', 'NAN', 'NONE', 'NAT', 'NULL']:
            return ""
        
        return prn_clean
    
    def _extract_fctc_data(self, data_rows: List[List], headers: List[str]) -> List[Dict]:
        """Extract only required fields from FCTC data"""
        
        # Create case-insensitive header mapping
        header_map = {}
        for i, header in enumerate(headers):
            if header:
                header_map[header.lower().strip()] = i
        
        # Define required field mappings (case-insensitive)
        field_mappings = {
            'timestamp': ['timestamp'],
            'email': ['email address', 'email'],
            'score': ['score', 'total score'],
            'full_name': ['full name- mandatory for all college students', 'full name', 'name'],
            'college_name': ['college name-mandatory for all college students ( please select your specific college name carefully and accurately )', 'college name', 'college'],
            'year': ['year-mandatory for all college students', 'year'],
            'roll_number': ['roll number-mandatory for all college students', 'roll number', 'roll no'],
            'branch': ['branch-mandatory only for non-vishwakarma institute of technology students', 'branch'],
            'division': ['division-mandatory only for non-vishwakarma institute of technology students', 'division'],
            'prn': ['prn - mandatory only for vishwakarma institute of technology students', 'prn'],
            'branch_division': ['branch-division- mandatory only for vishwakarma institute of technology students', 'branch-division', 'branch division']
        }
        
        # Find column indices for each field
        column_indices = {}
        for field, possible_names in field_mappings.items():
            for name in possible_names:
                if name in header_map:
                    column_indices[field] = header_map[name]
                    break
        
        # Check for critical fields
        if 'prn' not in column_indices:
            available_cols = list(headers)
            raise Exception(f"❌ FCTC FILE ERROR: Missing required PRN column\n"
                          f"Available columns: {available_cols}\n"
                          f"💡 Please ensure your FCTC file has a PRN column.")
        
        if 'score' not in column_indices:
            available_cols = list(headers)
            raise Exception(f"❌ FCTC FILE ERROR: Missing required Score column\n"
                          f"Available columns: {available_cols}\n"
                          f"💡 Please ensure your FCTC file has a Score column.")
        
        # Extract data
        extracted_data = []
        prn_scores = {}  # Track multiple attempts per PRN
        
        for row_idx, row in enumerate(data_rows):
            if not any(cell for cell in row):  # Skip empty rows
                continue
                
            # Ensure row has enough columns
            while len(row) < len(headers):
                row.append(None)
            
            # Extract PRN and validate
            prn_raw = row[column_indices['prn']] if len(row) > column_indices['prn'] else None
            prn_clean = self._clean_prn(prn_raw)
            
            if not prn_clean:
                continue  # Skip rows without PRN
            
            # Extract score and convert to float
            score_raw = row[column_indices['score']] if len(row) > column_indices['score'] else None
            try:
                score = float(score_raw) if score_raw is not None else 0.0
            except (ValueError, TypeError):
                score = 0.0
            
            # Handle multiple attempts - keep highest score
            if prn_clean in prn_scores:
                if score > prn_scores[prn_clean]['score']:
                    prn_scores[prn_clean] = {'score': score, 'row_data': row, 'prn_raw': prn_raw}
            else:
                prn_scores[prn_clean] = {'score': score, 'row_data': row, 'prn_raw': prn_raw}
        
        # Build final records from best attempts
        for prn_clean, data in prn_scores.items():
            row = data['row_data']
            record = {
                'PRN_RAW': data['prn_raw'],
                'PRN_CLEAN': prn_clean,
                'Score': data['score']
            }
            
            # Add optional fields
            for field, col_idx in column_indices.items():
                if field not in ['prn', 'score'] and len(row) > col_idx:
                    record[field.title()] = row[col_idx]
            
            extracted_data.append(record)
        
        if not extracted_data:
            raise Exception("❌ FCTC FILE ERROR: No valid data rows found with PRN and Score")
        
        return extracted_data
    
    def _extract_roll_call_data(self, data_rows: List[List], headers: List[str]) -> List[Dict]:
        """Extract roll call data with case-insensitive matching"""
        
        # Create case-insensitive header mapping
        header_map = {}
        for i, header in enumerate(headers):
            if header:
                header_map[header.lower().strip()] = i
        
        # Define required field mappings (case-insensitive)
        field_mappings = {
            'prn': ['prn'],
            'roll_no': ['roll no', 'roll number', 'sr.no', 'sr no', 'srno', 'serial no'],
            'name': ['name', 'student name', 'full name'],
            'division': ['division', 'div', 'section']
        }
        
        # Find column indices
        column_indices = {}
        for field, possible_names in field_mappings.items():
            for name in possible_names:
                if name in header_map:
                    column_indices[field] = header_map[name]
                    break
        
        # Check for required columns
        missing_cols = []
        for field in ['prn', 'roll_no', 'name', 'division']:
            if field not in column_indices:
                missing_cols.append(field.upper())
        
        if missing_cols:
            available_cols = list(headers)
            variations = {
                'PRN': 'PRN',
                'ROLL_NO': 'Roll No (or variations: Sr.no, Roll Number, Serial No)',
                'NAME': 'Name (or variations: Student Name, Full Name)',
                'DIVISION': 'Division (or variations: Division, DIV, dIV, div, DIVISION)'
            }
            
            missing_details = [f"• '{variations.get(col, col)}'" for col in missing_cols]
            
            raise Exception(f"❌ ROLL CALL FILE ERROR: Missing required columns\n"
                          f"Missing columns:\n" + "\n".join(missing_details) + "\n"
                          f"Available columns in your file:\n" + 
                          "\n".join([f"• '{col}'" for col in available_cols]) + "\n"
                          f"💡 Please ensure your Roll Call file has the exact column names listed above.")
        
        # Extract data
        extracted_data = []
        for row in data_rows:
            if not any(cell for cell in row):  # Skip empty rows
                continue
                
            # Ensure row has enough columns
            while len(row) < len(headers):
                row.append(None)
            
            # Extract PRN and validate
            prn_raw = row[column_indices['prn']] if len(row) > column_indices['prn'] else None
            prn_clean = self._clean_prn(prn_raw)
            
            if not prn_clean:
                continue  # Skip rows without PRN
            
            record = {
                'PRN_RAW': prn_raw,
                'PRN_CLEAN': prn_clean,
                'Roll_No': row[column_indices['roll_no']] if len(row) > column_indices['roll_no'] else None,
                'Name': row[column_indices['name']] if len(row) > column_indices['name'] else None,
                'Division': row[column_indices['division']] if len(row) > column_indices['division'] else None
            }
            
            extracted_data.append(record)
        
        if not extracted_data:
            raise Exception("❌ ROLL CALL FILE ERROR: No valid data rows found")
        
        return extracted_data
    
    def read_fctc_excel(self, file_path):
        """Read FCTC Excel file and extract ONLY required fields"""
        try:
            data_rows, headers = self._read_excel_with_header_detection(file_path)
            return self._extract_fctc_data(data_rows, headers)
        except Exception as e:
            raise Exception(f"Error reading FCTC Excel file: {str(e)}")
    
    def read_roll_call_excel(self, file_path):
        """Read Roll Call Excel file"""
        try:
            data_rows, headers = self._read_excel_with_header_detection(file_path)
            return self._extract_roll_call_data(data_rows, headers)
        except Exception as e:
            raise Exception(f"Error reading Roll Call Excel file: {str(e)}")
    
    def process_and_generate_reports(self, fctc_file_path, roll_call_file_path, year):
        """
        PRN-FIRST PIPELINE: Process files and generate attendance reports
        """
        try:
            # Read and extract data
            print("📖 Reading FCTC file...")
            fctc_data = self.read_fctc_excel(fctc_file_path)
            print(f"✅ FCTC file processed: {len(fctc_data)} records")
            
            print("📖 Reading Roll Call file...")
            roll_call_data = self.read_roll_call_excel(roll_call_file_path)
            print(f"✅ Roll Call file processed: {len(roll_call_data)} records")
            
            # Create PRN lookup sets
            fctc_prns = {record['PRN_CLEAN'] for record in fctc_data}
            roll_call_prns = {record['PRN_CLEAN'] for record in roll_call_data}
            
            print(f"🔍 FCTC unique PRNs: {len(fctc_prns)}")
            print(f"🔍 Roll Call unique PRNs: {len(roll_call_prns)}")
            
            # Find matches
            matched_prns = fctc_prns.intersection(roll_call_prns)
            print(f"✅ Matched PRNs: {len(matched_prns)}")
            
            if not matched_prns:
                raise Exception("❌ No matching PRNs found between FCTC and Roll Call files")
            
            # Create lookup dictionaries
            fctc_lookup = {record['PRN_CLEAN']: record for record in fctc_data}
            roll_call_lookup = {record['PRN_CLEAN']: record for record in roll_call_data}
            
            # Generate attendance report
            attendance_report = []
            for roll_record in roll_call_data:
                prn = roll_record['PRN_CLEAN']
                
                # Check if student appeared for exam
                if prn in fctc_lookup:
                    fctc_record = fctc_lookup[prn]
                    status = "Present"
                    score = fctc_record.get('Score', 'N/A')
                else:
                    status = "Absent"
                    score = "N/A"
                
                attendance_report.append({
                    'PRN': roll_record['PRN_RAW'],
                    'Roll_No': roll_record['Roll_No'],
                    'Name': roll_record['Name'],
                    'Division': roll_record['Division'],
                    'Attendance_Status': status,
                    'Score': score
                })
            
            # Return results (in serverless environment, we return data instead of saving files)
            result = {
                'success': True,
                'matched_students': len(matched_prns),
                'total_roll_call': len(roll_call_data),
                'total_fctc': len(fctc_data),
                'attendance_report': attendance_report,
                'reports': {
                    'files_created': ['attendance_report.json'],  # Virtual file names
                    'summary': f"Processed {len(matched_prns)} matched students out of {len(roll_call_data)} total students"
                }
            }
            
            return result
            
        except Exception as e:
            raise Exception(f"Error in PRN-first processing: {str(e)}")