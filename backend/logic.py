# Business logic for FCTC exam automation - MULTI-LEVEL MATCHING PIPELINE
import openpyxl
import os
import re
from typing import Dict, List, Tuple, Optional

class ExamProcessor:
    """
    MULTI-LEVEL MATCHING PIPELINE - EXTRACTS ONLY REQUIRED FIELDS FROM FCTC:
    
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
    
    MATCHING STRATEGY (Multi-Level):
    1. Level 1: PRN matching (primary, most reliable)
    2. Level 2: Name matching with fuzzy logic (handles typos, 80% similarity threshold)
    3. Level 3: Roll No + Division matching (unique combination per division)
    
    RULES:
    1. Try PRN match first (most reliable)
    2. If PRN fails, try Name match (handles typos/variations)
    3. If Name fails, try Roll No + Division match (unique per division)
    4. Track which method was used for each match
    5. FCTC file: Extract ONLY required fields, ignore all other columns
    6. Attendance logic: If matched by any method → Present, Else → Absent
    7. Missing critical columns (PRN, Score) = ABORT with clear error
    8. Missing optional fields = Continue processing with available fields
    9. Output includes "Match_Method" column showing how each student was matched
    """
    
    def __init__(self):
        pass
    
    def _read_excel_with_header_detection(self, file_path: str) -> Tuple[List[List], List[str]]:
        """
        Read Excel file and detect header row automatically with multiple fallback methods
        Returns: (data_rows, header_row)
        """
        print(f"🔍 Attempting to read Excel file: {file_path}")
        
        # Method 1: Try with pandas if available (most robust for problematic files)
        try:
            print("📖 Method 1: Trying pandas (if available)...")
            import pandas as pd
            
            # Try reading with pandas first (handles most Excel issues)
            df = pd.read_excel(file_path, header=None)
            
            if df.empty:
                raise Exception("Excel file is empty")
            
            # Convert DataFrame to list of lists
            all_rows = df.values.tolist()
            
            # Find header row (look for row with most non-empty string values)
            header_row_idx = 0
            max_string_count = 0
            
            for i, row in enumerate(all_rows[:10]):  # Check first 10 rows
                string_count = sum(1 for cell in row if isinstance(cell, str) and str(cell).strip())
                if string_count > max_string_count:
                    max_string_count = string_count
                    header_row_idx = i
            
            headers = [str(cell).strip() if cell is not None and str(cell) != 'nan' else "" for cell in all_rows[header_row_idx]]
            data_rows = all_rows[header_row_idx + 1:]
            
            print(f"✅ Method 1 successful: Found {len(headers)} columns, {len(data_rows)} data rows")
            return data_rows, headers
            
        except ImportError:
            print("📝 pandas not available - using openpyxl methods")
        except Exception as e1:
            print(f"❌ Method 1 failed: {str(e1)}")
        
        # Method 2: Try with openpyxl (data_only=True) - Enhanced for XML issues
        try:
            print("📖 Method 2: Trying openpyxl (data_only=True)...")
            
            workbook = openpyxl.load_workbook(file_path, data_only=True)
            sheet = workbook.active
            
            # Get all rows as lists
            all_rows = []
            for row in sheet.iter_rows(values_only=True):
                if any(cell is not None for cell in row):  # Skip completely empty rows
                    all_rows.append(list(row))
            
            workbook.close()
            
            if not all_rows:
                raise Exception("Excel file is empty")
            
            # Find header row
            header_row_idx = 0
            max_string_count = 0
            
            for i, row in enumerate(all_rows[:10]):
                string_count = sum(1 for cell in row if isinstance(cell, str) and cell.strip())
                if string_count > max_string_count:
                    max_string_count = string_count
                    header_row_idx = i
            
            headers = [str(cell).strip() if cell is not None else "" for cell in all_rows[header_row_idx]]
            data_rows = all_rows[header_row_idx + 1:]
            
            print(f"✅ Method 2 successful: Found {len(headers)} columns, {len(data_rows)} data rows")
            return data_rows, headers
            
        except Exception as e2:
            print(f"❌ Method 2 failed: {str(e2)}")
            
            # Method 3: Try with openpyxl (data_only=False)
            try:
                print("📖 Method 3: Trying openpyxl (data_only=False)...")
                
                workbook = openpyxl.load_workbook(file_path, data_only=False)
                sheet = workbook.active
                
                # Get all rows as lists
                all_rows = []
                for row in sheet.iter_rows(values_only=True):
                    if any(cell is not None for cell in row):
                        all_rows.append(list(row))
                
                workbook.close()
                
                if not all_rows:
                    raise Exception("Excel file is empty")
                
                # Find header row
                header_row_idx = 0
                max_string_count = 0
                
                for i, row in enumerate(all_rows[:10]):
                    string_count = sum(1 for cell in row if isinstance(cell, str) and cell.strip())
                    if string_count > max_string_count:
                        max_string_count = string_count
                        header_row_idx = i
                
                headers = [str(cell).strip() if cell is not None else "" for cell in all_rows[header_row_idx]]
                data_rows = all_rows[header_row_idx + 1:]
                
                print(f"✅ Method 3 successful: Found {len(headers)} columns, {len(data_rows)} data rows")
                return data_rows, headers
                
            except Exception as e3:
                print(f"❌ Method 3 failed: {str(e3)}")
                
                # Method 4: Try reading with read_only mode and ignore XML errors
                try:
                    print("📖 Method 4: Trying openpyxl read-only mode...")
                    
                    workbook = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
                    sheet = workbook.active
                    
                    all_rows = []
                    for row in sheet.iter_rows(values_only=True):
                        if any(cell is not None for cell in row):
                            all_rows.append(list(row))
                    
                    workbook.close()
                    
                    if not all_rows:
                        raise Exception("Excel file is empty")
                    
                    # Find header row
                    header_row_idx = 0
                    max_string_count = 0
                    
                    for i, row in enumerate(all_rows[:10]):
                        string_count = sum(1 for cell in row if isinstance(cell, str) and cell.strip())
                        if string_count > max_string_count:
                            max_string_count = string_count
                            header_row_idx = i
                    
                    headers = [str(cell).strip() if cell is not None else "" for cell in all_rows[header_row_idx]]
                    data_rows = all_rows[header_row_idx + 1:]
                    
                    print(f"✅ Method 4 successful: Found {len(headers)} columns, {len(data_rows)} data rows")
                    return data_rows, headers
                    
                except Exception as e4:
                    print(f"❌ Method 4 failed: {str(e4)}")
                    
                    # Method 5: Try with minimal openpyxl settings and error tolerance
                    try:
                        print("📖 Method 5: Trying openpyxl with error tolerance...")
                        
                        # Try to load with minimal settings
                        import tempfile
                        import shutil
                        
                        # Create a temporary copy
                        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
                            shutil.copy2(file_path, tmp_file.name)
                            tmp_path = tmp_file.name
                        
                        try:
                            # Try different openpyxl configurations
                            for keep_vba in [False, True]:
                                for keep_links in [False, True]:
                                    try:
                                        wb = openpyxl.load_workbook(
                                            tmp_path, 
                                            read_only=False, 
                                            keep_vba=keep_vba,
                                            data_only=True,
                                            keep_links=keep_links
                                        )
                                        ws = wb.active
                                        
                                        all_rows = []
                                        for row in ws.iter_rows(values_only=True, max_row=1000):  # Limit rows to avoid memory issues
                                            if any(cell is not None for cell in row):
                                                all_rows.append(list(row))
                                        
                                        wb.close()
                                        
                                        if all_rows:
                                            # Find header row
                                            header_row_idx = 0
                                            max_string_count = 0
                                            
                                            for i, row in enumerate(all_rows[:10]):
                                                string_count = sum(1 for cell in row if isinstance(cell, str) and cell.strip())
                                                if string_count > max_string_count:
                                                    max_string_count = string_count
                                                    header_row_idx = i
                                            
                                            headers = [str(cell).strip() if cell is not None else "" for cell in all_rows[header_row_idx]]
                                            data_rows = all_rows[header_row_idx + 1:]
                                            
                                            print(f"✅ Method 5 successful: Found {len(headers)} columns, {len(data_rows)} data rows")
                                            return data_rows, headers
                                    except:
                                        continue
                            
                            raise Exception("All openpyxl configurations failed")
                            
                        finally:
                            # Clean up temp file
                            try:
                                os.unlink(tmp_path)
                            except:
                                pass
                                
                    except Exception as e5:
                        print(f"❌ Method 5 failed: {str(e5)}")
                        
                        # All methods failed - provide comprehensive error message
                        error_details = f"""
❌ All Excel reading methods failed. This appears to be a severely corrupted Excel file.

🔧 SOLUTIONS TO TRY:

**Option 1 - Fix the Excel file:**
1. Open the file in Microsoft Excel
2. Select all data (Ctrl+A)
3. Copy it (Ctrl+C)  
4. Create a new Excel workbook
5. Paste the data (Ctrl+V)
6. Save as a new .xlsx file
7. Upload the new file

**Option 2 - Convert to CSV:**
1. Open the file in Excel
2. Save As → CSV format
3. Upload the CSV file instead

**Option 3 - Check file integrity:**
1. Ensure the file is not corrupted
2. Try opening in Google Sheets and re-downloading
3. Verify the file is a valid Excel format

**Technical Details:**
• Method 2 (openpyxl data_only=True): {str(e2)}
• Method 3 (openpyxl data_only=False): {str(e3)}
• Method 4 (read_only): {str(e4)}
• Method 5 (error tolerance): {str(e5)}

If none of these solutions work, the original file may be irreparably corrupted.
"""
                        raise Exception(error_details)
    
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
    
    def _clean_name(self, name_value) -> str:
        """Clean and normalize name for matching"""
        if name_value is None:
            return ""
        
        name_str = str(name_value).strip().upper()
        # Remove extra spaces
        name_str = re.sub(r'\s+', ' ', name_str)
        # Remove special characters but keep spaces
        name_str = re.sub(r'[^A-Z\s]', '', name_str)
        
        # Filter out invalid values
        if name_str in ['', 'NAN', 'NONE', 'NAT', 'NULL']:
            return ""
        
        return name_str
    
    def _clean_roll_no(self, roll_no_value) -> str:
        """Clean and normalize roll number"""
        if roll_no_value is None:
            return ""
        
        roll_str = str(roll_no_value).strip().upper()
        # Remove decimal points (Excel formatting)
        roll_str = re.sub(r'\.0+$', '', roll_str)
        # Remove any non-alphanumeric characters
        roll_clean = re.sub(r'[^\w]', '', roll_str)
        
        # Filter out invalid values
        if roll_clean in ['', 'NAN', 'NONE', 'NAT', 'NULL']:
            return ""
        
        return roll_clean
    
    def _fuzzy_name_match(self, name1: str, name2: str, threshold: float = 0.8) -> bool:
        """
        Check if two names match using Jaccard similarity
        Returns True if similarity >= threshold
        """
        if not name1 or not name2:
            return False
        
        # Convert to sets of words
        set1 = set(name1.split())
        set2 = set(name2.split())
        
        if not set1 or not set2:
            return False
        
        # Calculate Jaccard similarity
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        if union == 0:
            return False
        
        similarity = intersection / union
        return similarity >= threshold
    
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
        MULTI-LEVEL MATCHING PIPELINE: Process files and generate division-wise attendance reports
        Matching Priority: 1. PRN → 2. Name (fuzzy) → 3. Roll No + Division
        """
        try:
            # Read and extract data
            print("📖 Reading FCTC file...")
            fctc_data = self.read_fctc_excel(fctc_file_path)
            print(f"✅ FCTC file processed: {len(fctc_data)} records")
            
            print("📖 Reading Roll Call file...")
            roll_call_data = self.read_roll_call_excel(roll_call_file_path)
            print(f"✅ Roll Call file processed: {len(roll_call_data)} records")
            
            # Create multiple lookup dictionaries from FCTC data
            print("🔍 Creating lookup dictionaries for multi-level matching...")
            
            # Level 1: PRN lookup
            fctc_lookup_by_prn = {}
            for record in fctc_data:
                prn = record['PRN_CLEAN']
                if prn:
                    fctc_lookup_by_prn[prn] = record
            
            # Level 2: Name lookup (cleaned names)
            fctc_lookup_by_name = {}
            for record in fctc_data:
                name = self._clean_name(record.get('Full_Name', ''))
                if name:
                    # Store as list to handle duplicate names
                    if name not in fctc_lookup_by_name:
                        fctc_lookup_by_name[name] = []
                    fctc_lookup_by_name[name].append(record)
            
            # Level 3: Roll No + Division lookup
            fctc_lookup_by_roll_div = {}
            for record in fctc_data:
                roll_no = self._clean_roll_no(record.get('Roll_Number', ''))
                division = str(record.get('Division', '')).strip().upper()
                if roll_no and division:
                    key = f"{roll_no}_{division}"
                    fctc_lookup_by_roll_div[key] = record
            
            print(f"  ✓ PRN lookup: {len(fctc_lookup_by_prn)} entries")
            print(f"  ✓ Name lookup: {len(fctc_lookup_by_name)} entries")
            print(f"  ✓ Roll+Div lookup: {len(fctc_lookup_by_roll_div)} entries")
            
            # Track matching statistics
            match_stats = {
                'prn_matches': 0,
                'name_matches': 0,
                'roll_div_matches': 0,
                'no_match': 0
            }
            
            # Group students by division with multi-level matching
            divisions = {}
            for roll_record in roll_call_data:
                division = str(roll_record.get('Division', 'Unknown')).strip().upper()
                if not division or division == 'NONE' or division == 'NAN':
                    division = 'Unknown'
                
                if division not in divisions:
                    divisions[division] = []
                
                # Multi-level matching
                prn = roll_record['PRN_CLEAN']
                roll_name = self._clean_name(roll_record.get('Name', ''))
                roll_no = self._clean_roll_no(roll_record.get('Roll_No', ''))
                
                matched_record = None
                match_method = "Not_Found"
                
                # Level 1: Try PRN match
                if prn and prn in fctc_lookup_by_prn:
                    matched_record = fctc_lookup_by_prn[prn]
                    match_method = "PRN"
                    match_stats['prn_matches'] += 1
                
                # Level 2: Try Name match (fuzzy)
                elif roll_name:
                    # First try exact name match
                    if roll_name in fctc_lookup_by_name:
                        candidates = fctc_lookup_by_name[roll_name]
                        # If multiple candidates, try to match by division
                        if len(candidates) == 1:
                            matched_record = candidates[0]
                            match_method = "Name"
                            match_stats['name_matches'] += 1
                        else:
                            # Multiple candidates - try to match by division
                            for candidate in candidates:
                                cand_div = str(candidate.get('Division', '')).strip().upper()
                                if cand_div == division:
                                    matched_record = candidate
                                    match_method = "Name"
                                    match_stats['name_matches'] += 1
                                    break
                            # If no division match, take first candidate
                            if not matched_record:
                                matched_record = candidates[0]
                                match_method = "Name"
                                match_stats['name_matches'] += 1
                    
                    # If no exact match, try fuzzy matching
                    if not matched_record:
                        for fctc_name, candidates in fctc_lookup_by_name.items():
                            if self._fuzzy_name_match(roll_name, fctc_name):
                                # Found fuzzy match
                                if len(candidates) == 1:
                                    matched_record = candidates[0]
                                    match_method = "Name"
                                    match_stats['name_matches'] += 1
                                    break
                                else:
                                    # Multiple candidates - try to match by division
                                    for candidate in candidates:
                                        cand_div = str(candidate.get('Division', '')).strip().upper()
                                        if cand_div == division:
                                            matched_record = candidate
                                            match_method = "Name"
                                            match_stats['name_matches'] += 1
                                            break
                                    if matched_record:
                                        break
                
                # Level 3: Try Roll No + Division match
                if not matched_record and roll_no and division:
                    key = f"{roll_no}_{division}"
                    if key in fctc_lookup_by_roll_div:
                        matched_record = fctc_lookup_by_roll_div[key]
                        match_method = "Roll_Div"
                        match_stats['roll_div_matches'] += 1
                
                # Determine status and score
                if matched_record:
                    status = "Present"
                    score = matched_record.get('Score', 'N/A')
                else:
                    status = "Absent"
                    score = "N/A"
                    match_stats['no_match'] += 1
                
                divisions[division].append({
                    'PRN': roll_record['PRN_RAW'],
                    'Roll_No': roll_record['Roll_No'],
                    'Name': roll_record['Name'],
                    'Division': roll_record['Division'],
                    'Attendance_Status': status,
                    'Score': score,
                    'Match_Method': match_method
                })
            
            print(f"📊 Found {len(divisions)} divisions: {list(divisions.keys())}")
            print(f"🎯 Matching Statistics:")
            print(f"  ✓ PRN matches: {match_stats['prn_matches']}")
            print(f"  ✓ Name matches: {match_stats['name_matches']}")
            print(f"  ✓ Roll+Div matches: {match_stats['roll_div_matches']}")
            print(f"  ✗ No match (Absent): {match_stats['no_match']}")
            
            # Generate division-wise reports
            division_reports = {}
            for division, students in divisions.items():
                division_reports[division] = {
                    'students': students,
                    'total_students': len(students),
                    'present_count': sum(1 for s in students if s['Attendance_Status'] == 'Present'),
                    'absent_count': sum(1 for s in students if s['Attendance_Status'] == 'Absent')
                }
                print(f"  📋 Division {division}: {len(students)} students ({division_reports[division]['present_count']} present, {division_reports[division]['absent_count']} absent)")
            
            # Calculate total matched students
            total_matched = match_stats['prn_matches'] + match_stats['name_matches'] + match_stats['roll_div_matches']
            
            # Return results with division-wise data
            result = {
                'success': True,
                'matched_students': total_matched,
                'total_roll_call': len(roll_call_data),
                'total_fctc': len(fctc_data),
                'divisions': list(divisions.keys()),
                'division_count': len(divisions),
                'division_reports': division_reports,
                'match_stats': match_stats,
                'reports': {
                    'files_created': [f'attendance_report_division_{div}.csv' for div in divisions.keys()],
                    'summary': f"Processed {total_matched} matched students across {len(divisions)} divisions using multi-level matching"
                }
            }
            
            return result
            
        except Exception as e:
            raise Exception(f"Error in multi-level matching processing: {str(e)}")