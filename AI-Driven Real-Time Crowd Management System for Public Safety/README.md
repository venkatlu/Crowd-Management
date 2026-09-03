# AI-Driven Real-Time Crowd Management System

A comprehensive real-time crowd monitoring and safety management system that helps security teams, event organizers, and public safety officials monitor and manage crowds across multiple areas of a venue or facility.

## 🚀 Features

### Core Capabilities
- **Multi-Zone Monitoring**: Monitor 5 different areas simultaneously (Ground floor, Hall, Balcony, Lobby entrance, Parking exit)
- **AI-Powered Detection**: Automatic people counting using YOLO computer vision
- **Real-Time Dashboard**: Live monitoring interface accessible from any device
- **Smart Safety Alerts**: Automatic notifications with customizable thresholds
- **Anomaly Detection**: Identify unusual crowd behavior patterns
- **Historical Analysis**: Export data and generate reports
- **Emergency Override**: Manual emergency alert system

### Technical Features
- **SQLite Database**: Lightweight, file-based database for easy setup
- **WebSocket Support**: Real-time communication for live updates
- **RESTful API**: Complete API for integration and data access
- **Responsive UI**: Modern, mobile-friendly dashboard
- **Multi-Channel Notifications**: SMS and Email alerts
- **Comprehensive Testing**: Full test suite included

## 📋 Prerequisites

- Python 3.8 or higher
- OpenCV compatible camera or video files
- Internet connection for YOLO model download (first run only)

## 🛠️ Installation

1. **Clone or download the project**
   ```bash
   cd "AI-Driven Real-Time Crowd Management System for Public Safety"
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   # The .env file is already created with default values
   # You can modify it if needed
   cat .env
   ```

4. **Verify video files**
   ```bash
   ls videos/
   # Should show: balcony_view.mp4, ground_crowd.mp4, hall_event.mp4, lobby_entrance.mp4, parking_exit.mp4
   ```

## 🚀 Quick Start

1. **Start the system**
   ```bash
   python start.py
   ```

2. **Access the dashboard**
   - Open your browser and go to: `http://localhost:8000`
   - The dashboard will show real-time crowd monitoring for all zones

3. **API Documentation**
   - Visit: `http://localhost:8000/docs` for interactive API documentation

## 📊 System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Video Sources │    │  AI People       │    │  Real-Time      │
│   (5 Zones)     │───▶│  Counter (YOLO)  │───▶│  Dashboard      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │  SQLite Database │
                       │  + Notifications │
                       └──────────────────┘
```

## 🎯 Zone Configuration

The system monitors 5 zones with the following default capacities:

| Zone | Capacity | Video Source |
|------|----------|--------------|
| Ground Floor | 100 people | `videos/ground_crowd.mp4` |
| Hall | 200 people | `videos/hall_event.mp4` |
| Balcony | 50 people | `videos/balcony_view.mp4` |
| Lobby | 30 people | `videos/lobby_entrance.mp4` |
| Parking | 40 people | `videos/parking_exit.mp4` |

## ⚙️ Configuration

### Alert Thresholds
- **Green**: ≤ 30% capacity (Safe)
- **Yellow**: 31-60% capacity (Warning)
- **Red**: > 60% capacity (Critical)

### Notification Settings
- **SMS**: Sent to security staff for Yellow and Red alerts
- **Email**: Sent to management for Yellow and Red alerts
- **Cooldown**: 5 minutes between alerts for the same zone

## 📱 Dashboard Features

### Real-Time Monitoring
- Live crowd counts for each zone
- Color-coded density indicators
- Progress bars showing capacity percentage
- Anomaly detection indicators

### Charts and Analytics
- Crowd trends over time
- Zone distribution pie chart
- Historical data visualization

### Alert Management
- Recent alerts list
- Alert resolution system
- Emergency override functionality

## 🔧 API Endpoints

### Core Endpoints
- `GET /api/status` - Get current system status
- `GET /api/zones` - Get zone configurations
- `GET /api/zone/{zone_name}/history` - Get zone historical data
- `GET /api/alerts` - Get recent alerts
- `POST /api/alert/{alert_id}/resolve` - Resolve an alert
- `POST /api/emergency/{zone_name}` - Send emergency alert

### WebSocket
- `ws://localhost:8000/ws` - Real-time updates

## 🧪 Testing

Run the comprehensive test suite:

```bash
python test_system.py
```

Or with pytest:
```bash
pytest test_system.py -v
```

## 📈 Data Export

The dashboard includes data export functionality:
- Export current zone data as CSV
- Historical data analysis
- Performance metrics

## 🔒 Security Features

- Input validation and sanitization
- SQL injection prevention
- Rate limiting on API endpoints
- Secure WebSocket connections

## 🚨 Emergency Features

### Emergency Override
- Manual emergency alert system
- Immediate notifications to all contacts
- Zone-specific emergency messages

### Anomaly Detection
- Automatic detection of unusual crowd patterns
- Configurable sensitivity settings
- Historical pattern analysis

## 📊 Monitoring Zones

### Ground Floor
- **Capacity**: 100 people
- **Typical Use**: Main event area, general admission
- **Monitoring**: High-density crowd management

### Hall
- **Capacity**: 200 people
- **Typical Use**: Large events, presentations
- **Monitoring**: Seated and standing crowd analysis

### Balcony
- **Capacity**: 50 people
- **Typical Use**: VIP areas, overflow seating
- **Monitoring**: Elevated crowd safety

### Lobby
- **Capacity**: 30 people
- **Typical Use**: Entry/exit control
- **Monitoring**: Queue management and flow control

### Parking
- **Capacity**: 40 people
- **Typical Use**: Vehicle area monitoring
- **Monitoring**: Pedestrian safety in vehicle areas

## 🔧 Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   # Check what's using port 8000
   lsof -i :8000
   # Kill the process or change port in config.py
   ```

2. **Video files not found**
   - Ensure all video files are in the `videos/` directory
   - Check file permissions and formats

3. **YOLO model download issues**
   - Ensure internet connection for first run
   - Check firewall settings

4. **Database issues**
   - SQLite database is created automatically
   - Check file permissions in the project directory

### Logs
- System logs are written to `crowd_management.log`
- Check logs for detailed error information

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Check the troubleshooting section
- Review the API documentation at `/docs`
- Check system logs for error details

## 🔄 Updates

### Version 1.0.0
- Initial release with SQLite database
- Complete multi-zone monitoring system
- Real-time dashboard with WebSocket support
- Comprehensive alert and notification system
- Full test suite and documentation

---