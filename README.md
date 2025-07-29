# README.md
# New Grad Job Scraper

Automated scraper that monitors 50+ top tech companies for new graduate software engineering positions.

## Features

- 🏢 **50+ Companies**: Monitors major tech companies including FAANG and unicorns
- 🔄 **3x Daily**: Runs automatically at 8AM, 2PM, and 8PM UTC via GitHub Actions
- 📧 **Email Alerts**: Get notified immediately when new jobs are found
- 📊 **Excel Reports**: Detailed reports with job breakdown and company statistics
- 🔍 **Smart Filtering**: Automatically identifies new grad vs senior roles
- 📈 **Change Tracking**: Compares with previous runs to show only new opportunities

## Quick Setup

### 1. Fork this repository

### 2. Set up email notifications
Go to your repository Settings → Secrets and variables → Actions, and add these secrets:

```
EMAIL_USER=your_email@gmail.com
EMAIL_PASSWORD=your_app_password  # Gmail app password, not regular password
RECIPIENT_EMAIL=where_to_send_alerts@gmail.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

### 3. Enable GitHub Actions
- Go to Actions tab in your forked repo
- Click "I understand my workflows, go ahead and enable them"

### 4. Test the scraper
- Go to Actions → New Grad Job Scraper → Run workflow
- Monitor the run to ensure everything works

## Configuration

### Adding/Modifying Companies
Edit `companies_config.json` to:
- Add new companies
- Disable companies (`"enabled": false`)
- Update selectors if websites change
- Modify search parameters

### Example company configuration:
```json
{
  "CompanyName": {
    "enabled": true,
    "careers_url": "https://company.com/careers",
    "search_params": {
      "keywords": "new grad software engineer"
    },
    "selectors": {
      "job_container": ".job-item",
      "title": ".job-title", 
      "location": ".job-location",
      "url": ".job-title a"
    }
  }
}
```

### Customizing Schedule
Edit `.github/workflows/job_scraper.yml` to change the cron schedule:
```yaml
schedule:
  - cron: '0 8,14,20 * * *'  # 8AM, 2PM, 8PM UTC
```

## Manual Usage

Run locally:
```bash
# Install dependencies
pip install -r requirements.txt

# Run scraper
python scraper.py --config companies_config.json

# Generate Excel report from JSON
python scraper.py --excel-only --input job_results_20231201_120000.json
```

## Output Files

- `job_results_TIMESTAMP.json`: Raw scraping results
- `new_grad_jobs_report_TIMESTAMP.xlsx`: Excel report with multiple sheets
- `latest_results.json`: Latest results for comparison tracking

## Excel Report Structure

1. **New Grad Jobs**: All found positions with details
2. **Summary**: Scraping statistics and overview  
3. **Company Breakdown**: Jobs count per company
4. **Errors**: Any scraping failures

## Troubleshooting

### No jobs found for a company
1. Check if the company's career page structure changed
2. Update selectors in `companies_config.json`
3. Test with a single company: `python scraper.py --config test_config.json`

### Email notifications not working
1. Verify GitHub Secrets are set correctly
2. For Gmail, use App Password instead of regular password
3. Check Actions logs for detailed error messages

### GitHub Actions failing
1. Check the Actions tab for error logs
2. Ensure all secrets are properly configured
3. Verify requirements.txt has all dependencies

## Rate Limiting & Ethics

The scraper includes:
- Random delays between requests (1-3 seconds)
- Respectful rate limiting between companies (2-5 seconds)
- User-Agent rotation to avoid detection
- Error handling to prevent infinite loops

## Contributing

1. Fork the repository
2. Add new companies to `companies_config.json`
3. Test your changes locally
4. Submit a Pull Request

## License

MIT License - Feel free to use and modify for your job search!

---

# Setup Instructions for Gmail App Password

## Gmail App Password Setup

Since Gmail requires app passwords for automated email sending, follow these steps:

1. **Enable 2-Factor Authentication**:
   - Go to Google Account settings
   - Security → 2-Step Verification → Turn on

2. **Generate App Password**:
   - Go to Google Account → Security
   - 2-Step Verification → App passwords
   - Select "Mail" and your device
   - Copy the 16-character password

3. **Add to GitHub Secrets**:
   - Repository Settings → Secrets and variables → Actions
   - Add `EMAIL_PASSWORD` with the app password (not your regular password)

## Environment Variables for Local Testing

Create a `.env` file (not committed to git):
```
EMAIL_USER=your_email@gmail.com
EMAIL_PASSWORD=your_16_char_app_password
RECIPIENT_EMAIL=alerts@gmail.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

# Setup Instructions for Gmail App Password

## Gmail App Password Setup

Since Gmail requires app passwords for automated email sending, follow these steps:

1. **Enable 2-Factor Authentication**:
   - Go to Google Account settings
   - Security → 2-Step Verification → Turn on

2. **Generate App Password**:
   - Go to Google Account → Security
   - 2-Step Verification → App passwords
   - Select "Mail" and your device
   - Copy the 16-character password

3. **Add to GitHub Secrets**:
   - Repository Settings → Secrets and variables → Actions
   - Add `EMAIL_PASSWORD` with the app password (not your regular password)
