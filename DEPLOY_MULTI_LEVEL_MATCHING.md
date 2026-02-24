# Deploy Multi-Level Matching to Vercel

## Quick Deployment Steps

### Option 1: Vercel Dashboard (Recommended)

1. Go to: https://vercel.com/
2. Login with: pranavyehale36@gmail.com
3. Select project: `fctc_automation_system`
4. Click "Deployments" tab
5. Find the latest deployment and click "Redeploy"
6. Or click "Deploy" and use commit hash: **4e28bdb**

### Option 2: Automatic Deployment

If you have GitHub integration enabled:
- The push to GitHub should trigger automatic deployment
- Check the "Deployments" tab to see if it's deploying
- Wait for deployment to complete (usually 2-3 minutes)

### Verify Deployment

After deployment completes:

1. Go to your Vercel project URL
2. Upload test files (FCTC + Roll Call)
3. Check the downloaded CSV files for the new **Match_Method** column
4. Verify that students are being matched by different methods

### What Changed

**Commit**: `4e28bdb`
**Message**: "Implement multi-level matching: PRN, Name (fuzzy), Roll+Division"

**Key Changes**:
- Added 3-level matching: PRN → Name (fuzzy) → Roll No + Division
- New column in output: `Match_Method`
- Better handling of students with wrong/empty PRN
- Matching statistics in console logs

### Expected Results

Students will now be matched using:
1. **PRN** (if available and correct)
2. **Name** (if PRN fails, uses fuzzy matching for typos)
3. **Roll No + Division** (if both above fail, unique per division)

This significantly reduces false "Absent" markings!

### Troubleshooting

If deployment fails:
- Check Vercel deployment logs
- Ensure `requirements.txt` has no pandas (should only have openpyxl, Flask, etc.)
- Verify `runtime.txt` has `python-3.9`
- Check that all files are committed and pushed to GitHub

### Repository Info

- **GitHub**: https://github.com/PranavYehale/FCTC-TOOL
- **Branch**: master
- **Latest Commit**: 4e28bdb
- **Vercel Project**: fctc_automation_system
