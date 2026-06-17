# SCMXpertLite

A comprehensive supply chain management application with real-time data processing capabilities.

## Project Overview

SCMXpertLite is a full-stack application designed for managing supply chain operations, including shipment tracking, device data management, and user authentication. The system leverages Apache Kafka for real-time data streaming and provides a modern web interface for administrators and users.

## Architecture

### Components

- **Backend**: FastAPI-based REST API with database integration
- **Frontend**: HTML/JavaScript web interface for dashboards and data management
- **Kafka**: Real-time event streaming for producer and consumer services
- **Database**: Integrated database layer for persistent storage
- **Docker**: Containerized deployment for backend, producer, and consumer services

### Directory Structure

```
├── backend/                    # FastAPI backend application
│   ├── main.py               # Main application entry point
│   ├── models.py             # Database models
│   ├── db.py                 # Database configuration
│   ├── auth_utils.py         # Authentication utilities
│   ├── user.py               # User management
│   ├── device_data.py        # Device data operations
│   ├── shipments_da.py       # Shipment data access
│   ├── admin_privileges.py   # Admin privilege management
│   ├── role_management.py    # Role-based access control
│   └── requirements.txt       # Python dependencies
│
├── frontend/                  # Web UI templates
│   ├── dashboard.html        # User dashboard
│   ├── admin_dashboard.html  # Admin dashboard
│   ├── device_data.html      # Device data interface
│   ├── shipment_data.html    # Shipment data interface
│   ├── user.html             # User management interface
│   ├── profile.html          # User profile page
│   ├── settings.html         # Settings page
│   └── logout.html           # Logout page
│
├── kafka/                     # Kafka services
│   ├── producer/             # Kafka producer service
│   └── consumer/             # Kafka consumer service
│
├── docker-compose.yml        # Docker composition file
├── producer.py               # Standalone producer script
├── consumer.py               # Standalone consumer script
└── README.md                 # This file
```

## Getting Started

### Prerequisites

- Python 3.8+
- Docker and Docker Compose (for containerized setup)
- Apache Kafka
- Database (configured in backend)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd scmxpertlite
   ```

2. **Backend Setup**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Environment Configuration**
   - Create a `.env` file in the backend directory with necessary configuration
   - Update database connection strings and Kafka broker addresses

### Running the Application

#### Option 1: Docker Compose (Recommended)
```bash
docker-compose up -d
```

This will start:
- Backend API
- Kafka Producer
- Kafka Consumer
- All associated services

#### Option 2: Local Development

**Backend**:
```bash
cd backend
python main.py
```

**Kafka Producer** (in separate terminal):
```bash
python producer.py
```

**Kafka Consumer** (in separate terminal):
```bash
python consumer.py
```

## Features

### User Management
- User registration and authentication
- Role-based access control (RBAC)
- Password management and recovery
- User profile and settings management

### Admin Capabilities
- Admin dashboard for system monitoring
- User privilege management
- Role assignment and management
- System-wide settings configuration

### Supply Chain Operations
- **Device Data Management**: Track and manage IoT device data
- **Shipment Management**: Monitor and manage shipments
- **Real-time Processing**: Kafka-based event streaming for data updates
- **Data Analytics**: Dashboard views for insights

## API Endpoints

The backend provides RESTful API endpoints for:
- User authentication and management (`/users`, `/auth`)
- Device data operations (`/devices`)
- Shipment operations (`/shipments`)
- Admin functions (`/admin`)

## Database Models

- **Users**: User accounts and authentication
- **Devices**: IoT device information
- **Shipments**: Shipment records and tracking
- **Roles**: Role definitions and permissions

## Configuration

### Backend Configuration
See `backend/db.py` and `backend/main.py` for database and application configuration.

### Kafka Configuration
Kafka broker addresses and topics can be configured in the producer and consumer scripts.

### Docker Configuration
Modify `docker-compose.yml` to adjust service configuration, ports, and environment variables.

## Development

### Backend Development
- Framework: FastAPI
- Database: SQLAlchemy (as evidenced by models structure)
- Authentication: Custom auth utilities

### Frontend Development
- Static HTML templates with embedded JavaScript
- Responsive design for admin and user dashboards

## Troubleshooting

### Database Connection Issues
- Verify database credentials in configuration
- Ensure database service is running

### Kafka Connection Issues
- Check Kafka broker is accessible
- Verify broker address in configuration

### API Connection Issues
- Verify backend service is running
- Check API port configuration
- Review application logs

## License

[Add your license information here]

## Support

For issues and questions, please contact the development team or refer to the project documentation.

---

**Last Updated**: 2026-06-17
