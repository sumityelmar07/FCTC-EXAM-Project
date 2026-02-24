# Multi-Level Matching Implementation Plan

## Problem Statement
Students sometimes:
- Enter wrong PRN
- Leave PRN empty
- Have typos in their names
- Can only be identified by Roll No + Division combination

## Solution: Multi-Level Matching Strategy

### Matching Priority (in order):

1. **Level 1: PRN Matching** (Primary - Most Reliable)
   - Clean and normalize PRN from both files
   - Direct PRN match
   - If match found → MATCHED

2. **Level 2: Name Matching** (Secondary - Handles Typos)
   - Clean and normalize names
   - Fuzzy matching with 80% similarity threshold
   - Handles minor typos and variations
   - If match found → MATCHED (with flag "matched_by_name")

3. **Level 3: Roll No + Division Matching** (Tertiary - Unique Combination)
   - Clean Roll No from both files
   - Match Roll No + Division combination
   - This is unique per division
   - If match found → MATCHED (with flag "matched_by_roll_div")

### Implementation Details:

#### Helper Methods to Add:
```python
def _clean_name(self, name_value) -> str:
    # Normalize name for matching
    
def _clean_roll_no(self, roll_no_value) -> str:
    # Normalize roll number
    
def _fuzzy_name_match(self, name1: str, name2: str, threshold: float = 0.8) -> bool:
    # Check name similarity using Jaccard similarity
    
def _find_student_match(self, fctc_record, roll_call_data, fctc_lookup_by_name, fctc_lookup_by_roll_div):
    # Multi-level matching logic
```

#### Matching Process:
1. Create multiple lookup dictionaries from FCTC data:
   - By PRN (existing)
   - By cleaned Name
   - By Roll No + Division combination

2. For each roll call student:
   - Try PRN match first
   - If no PRN match, try Name match
   - If no Name match, try Roll No + Division match
   - Track which method was used for matching

3. Return match result with metadata:
   - Student data
   - Match method used
   - Match confidence

### Benefits:
- Catches students with wrong/empty PRN
- Handles name typos
- Uses Roll No + Division as fallback
- Provides transparency on how each student was matched
- Reduces false "Absent" markings

### Output Enhancement:
Add "Match_Method" column to reports:
- "PRN" - Matched by PRN
- "Name" - Matched by name similarity
- "Roll_Div" - Matched by Roll No + Division
- "Not_Found" - No match found (Absent)

This provides transparency and helps identify data quality issues.
