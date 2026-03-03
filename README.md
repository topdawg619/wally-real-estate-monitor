# 🏠 Wally - Real Estate Monitoring System

**Open-source real estate monitoring system for tracking 5BR/3BA homes across multiple listing sites**

Built specifically for Chula Vista, CA (zip code 91913) and surrounding areas, but easily configurable for any market.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/topdawg619/wally-real-estate-monitor.git
cd wally-real-estate-monitor

# Setup everything (installs dependencies, creates database, configures monitoring)
python setup.py setup

# Test the system
python setup.py test

# Start the web dashboard
python setup.py dashboard
# Opens automatically at http://localhost:8080
```

## ✨ Features

### 🕷️ **Multi-Site Scraping**
- **Redfin.com** - Advanced search with JSON data extraction
- **Realtor.com** - Property card parsing and MLS integration
- **Zillow.com** - Careful scraping with anti-bot protection
- **Respectful scraping** with proper delays and error handling

### 📊 **Intelligent Monitoring**
- **Automated scanning** 3 times daily (morning, afternoon, evening)
- **Smart filtering** for 5BR/3BA+ homes in target ZIP codes
- **Price change detection** with historical tracking
- **New listing alerts** within hours of posting
- **Status monitoring** (active, pending, sold, back on market)

### 🖥️ **Beautiful Dashboard**
- **Mobile-responsive design** optimized for daily checking
- **Advanced filtering** by ZIP code, price range, source, date
- **Recent activity feed** highlighting new listings and changes  
- **Favorites system** with notes and property tracking
- **Market insights** with charts and trend analysis

### 🎯 **Target Market**
- **Primary**: Chula Vista, CA (91913) - $857K median
- **Secondary**: 91910 ($790K), 91911 ($725K), 91915 ($833K), 92154 ($711K)
- **Focus**: 5BR/3BA homes in $900K-$1.2M range
- **Easily configurable** for any market or criteria

## 🔧 Installation & Setup

### Requirements
- Python 3.8 or higher
- Internet connection
- 50MB free disk space

### Automated Setup
```bash
python setup.py setup
```

This will:
- Install all required dependencies
- Create the SQLite database
- Configure monitoring schedules  
- Set up the web dashboard
- Create demo data for testing

### Manual Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
python src/database_manager.py

# Configure monitoring
cp config/config.example.json config/config.json
# Edit config.json with your preferences
```

## 📱 Usage

### Web Dashboard
```bash
python setup.py dashboard
```
Opens the responsive web interface at `http://localhost:8080`

### Command Line Monitoring
```bash
# Run a single scan
python src/property_monitor.py

# Run with specific ZIP codes
python src/property_monitor.py --zips 91913,91910,91911

# Monitor specific sites only
python src/property_monitor.py --sites redfin,zillow
```

### Automated Monitoring
```bash
# Install cron jobs for automatic monitoring
python setup.py monitor

# Monitor manually runs:
# - 7:00 AM: Morning scan
# - 1:00 PM: Afternoon scan  
# - 7:00 PM: Evening scan
```

## 🏗️ Project Structure

```
wally-real-estate-monitor/
├── README.md                 # This file
├── setup.py                  # Easy setup and management
├── requirements.txt          # Python dependencies
├── config/
│   ├── config.json          # Main configuration
│   └── zip_codes.json       # Target ZIP code areas
├── src/
│   ├── scrapers/
│   │   ├── base_scraper.py   # Base scraping framework
│   │   ├── redfin_scraper.py # Redfin.com scraper
│   │   ├── realtor_scraper.py# Realtor.com scraper
│   │   └── zillow_scraper.py # Zillow.com scraper
│   ├── database_manager.py   # SQLite database management
│   ├── property_monitor.py   # Main monitoring coordinator
│   └── web_dashboard.py      # Web interface server
├── dashboard/
│   ├── index.html           # Main dashboard page
│   ├── css/
│   │   └── styles.css       # Responsive styling
│   └── js/
│       └── dashboard.js     # Interactive functionality
├── scripts/
│   ├── demo_data.py         # Generate demo listings
│   ├── install_cron.py      # Setup automated monitoring
│   └── backup_database.py   # Database backup utility
├── docs/
│   ├── setup-guide.md       # Detailed setup instructions
│   ├── configuration.md     # Configuration options
│   └── api.md               # API documentation
└── tests/
    ├── test_scrapers.py     # Scraper unit tests
    ├── test_database.py     # Database tests
    └── test_monitoring.py   # Integration tests
```

## 🎯 Configuration

### Target ZIP Codes
Edit `config/zip_codes.json` to monitor different areas:

```json
{
  "primary": ["91913"],
  "secondary": ["91910", "91911", "91915", "91917", "92154"],
  "names": {
    "91913": "Chula Vista East",
    "91910": "Chula Vista Central", 
    "91911": "Chula Vista West"
  }
}
```

### Property Criteria
Edit `config/config.json` for different search parameters:

```json
{
  "bedrooms_min": 5,
  "bathrooms_min": 3,
  "price_max": 1200000,
  "property_types": ["Single Family", "Townhouse"],
  "monitoring": {
    "scan_frequency": "3x_daily",
    "scan_times": ["07:00", "13:00", "19:00"]
  }
}
```

## 🔍 Market Intelligence

### Price Ranges (Chula Vista Area)
- **Good Deals**: <$900K (immediate alerts)
- **Watch List**: $900K-$1.05M (daily digest)  
- **Market Rate**: $1.05M-$1.2M (weekly summary)
- **Overpriced**: >$1.2M (informational only)

### Market Timing
- **Spring**: High activity, competitive pricing
- **Summer**: Peak season, quick sales
- **Fall**: Slower market, better negotiations
- **Winter**: Best deals, motivated sellers

### Days on Market
- **0-15 days**: Hot property (act fast)
- **16-30 days**: Normal market activity
- **31+ days**: Opportunity for negotiation

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup
```bash
# Clone for development
git clone https://github.com/topdawg619/wally-real-estate-monitor.git
cd wally-real-estate-monitor

# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest tests/

# Start development server
python src/web_dashboard.py --debug
```

### Adding New Markets
1. Research target ZIP codes and price ranges
2. Update `config/zip_codes.json` with new areas
3. Test scraping with `python setup.py test`
4. Submit pull request with market data

### Adding New Sites
1. Create new scraper in `src/scrapers/`
2. Follow the `base_scraper.py` framework
3. Add site configuration to `config/config.json`
4. Add tests in `tests/test_scrapers.py`

## 📊 Analytics & Insights

The dashboard provides comprehensive market analytics:

- **New Listings Tracking**: See properties as they hit the market
- **Price Change History**: Monitor price adjustments over time
- **Market Trends**: Understand seasonal patterns and market shifts
- **Inventory Levels**: Track available properties in your price range
- **Time on Market**: Identify properties that may be good negotiation opportunities

## ⚖️ Legal & Ethical Usage

- **Respectful Scraping**: Built-in delays and rate limiting
- **Personal Use**: Intended for individual home buyers and investors
- **No Commercial Resale**: Don't resell scraped data
- **Terms of Service**: Users responsible for compliance with site ToS
- **Rate Limiting**: Automatic throttling prevents site overload

## 🔒 Privacy & Security

- **Local Storage**: All data stored locally in SQLite database
- **No Data Transmission**: No external APIs or data sharing
- **Configurable**: Full control over what data is collected
- **Open Source**: Complete transparency in data handling

## 📈 Performance

- **Lightweight**: <50MB disk space, minimal CPU usage
- **Efficient**: Smart caching reduces redundant requests
- **Scalable**: Handles hundreds of properties across multiple markets
- **Reliable**: Automatic error recovery and retry logic

## 🛠️ Troubleshooting

### Common Issues

**"No properties found"**
- Check ZIP codes in `config/zip_codes.json`
- Verify internet connection
- Run `python setup.py test` to diagnose

**"Dashboard won't load"**
- Ensure port 8080 is available
- Check `python src/web_dashboard.py --port 8081`
- Look for error messages in console

**"Scraping errors"**
- Sites may have changed their structure
- Check for updates: `git pull origin main`
- Report issues on GitHub

### Getting Help

1. **Check Documentation**: See `docs/` folder for detailed guides
2. **Run Diagnostics**: Use `python setup.py test` to identify issues
3. **GitHub Issues**: Report bugs and request features
4. **Discussions**: Join community discussions for tips and support

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Built by the OpenClaw Agent Team:
- **Colin**: Technical infrastructure and scraping engine
- **Gordon**: Agent framework and deployment architecture  
- **Samantha**: Market research and Chula Vista area analysis
- **Jordan**: User experience and dashboard design

Special thanks to the real estate community for feedback and feature requests.

## 📞 Support

- **GitHub Issues**: Bug reports and feature requests
- **Discussions**: Community Q&A and tips
- **Documentation**: Comprehensive guides in `docs/` folder

---

**Happy house hunting! 🏠** 

Made with ❤️ for home buyers who want to stay ahead of the market.