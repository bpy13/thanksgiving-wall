# Thanksgiving Wall

A real-time thanksgiving message and photo sharing application built for church meetings. Members can upload thanksgiving messages with photos, and all submissions are displayed live on a beautiful slideshow with a YouTube-like layout.

## Features

- **Real-time Display**: WebSocket-powered live updates - new submissions appear instantly
- **Photo Slideshow**: Automatic rotation of uploaded photos with message overlays
- **YouTube-like Layout**: 75% images section, 25% message feed
- **Smart Queue System**: Priority display for new uploads, seamless rotation
- **Chinese Localization**: Full Chinese interface with GMT+8 timezone support

## Architecture

### Services
- **Upload Server** (Port 8000): Handles form submissions, image validation, database writes
- **Display Server** (Port 8001): Serves the live display page, manages WebSocket connections
- **PostgreSQL 17**: Database with timezone configuration and optimized queries
- **Docker Compose**: Multi-container orchestration

### Real-time Flow
1. User uploads message/photo → Upload server validates and stores
2. Upload server broadcasts via WebSocket → Display server receives
3. Display server pushes to all connected clients → Instant live updates

## Quick Start

### Prerequisites
- Docker and Docker Compose
- At least 1 GB RAM for smooth operation

### Deployment
```bash
# Clone the repository
git clone https://github.com/bpy13/thanksgiving-wall
cd thanksgiving-wall
# Start all services
docker-compose up -d
# Upload page: http://localhost:8000
# Display page: http://localhost:8001
```

## Usage

### For Congregation Members
1. Visit the upload URL on your phone/tablet
2. Fill in your thanksgiving message (required)
3. Add your name and group (optional)
4. Attach a photo (optional)
5. Submit - your message appears on the main display instantly!

### For Display Management
1. Open the display URL on the presentation screen
2. Messages appear in real-time on the right sidebar
3. Photos rotate automatically every 10 seconds on the left
4. New photos get priority display and join the rotation
5. System automatically refreshes content when queues empty

## Configuration

### Environment Variables
```yaml
# docker-compose.yml
environment:
  POSTGRES_DB: thanksgiving_db
  POSTGRES_USER: thanksgiving_user  
  POSTGRES_PASSWORD: your_secure_password
  POSTGRES_HOST: postgres
  POSTGRES_PORT: 5432
  DISPLAY_SERVICE_URL: http://display-server:8001
```

### Database Schema
- **messages**: Text messages with metadata and timezone info
- **images**: Photos with associated messages and metadata
- **Timezone**: Configured for Asia/Hong_Kong (GMT+8)

### Performance Settings
- **Image Limit**: Latest 10 images in rotation (configurable)
- **Message Limit**: Latest 20 messages in feed (configurable)
- **Rotation Speed**: 10-second intervals (configurable)
- **Auto-refresh**: Smart database refresh when content exhausted

## Privacy & Security

### Data Handling
- **Local Storage**: All data stored in self-hosted PostgreSQL
- **No External APIs**: No third-party services or data sharing
- **Image Validation**: Secure PIL-based processing prevents malicious uploads

### Production Considerations
```bash
# Strong database credentials
POSTGRES_PASSWORD=generate_secure_password_here
# Regular backups
docker exec postgres pg_dump -U thanksgiving_user thanksgiving_db > backup.sql
# Auto-cleanup old data (optional)
# Add cron job to remove messages older than 30 days
```

## UI/UX Features

### Upload Interface
- Clean Chinese form with red required field indicators
- Green submit button for clear action differentiation
- Instant validation feedback
- Mobile-responsive design

### Display Interface
- Black theme for professional church presentation
- YouTube-like layout optimized for projection
- Smooth animations and transitions
- Auto-reconnecting WebSocket with status indicator
- Chinese placeholder messages for empty states

## Technical Specifications

- **Backend**: FastAPI with async/await, WebSocket support
- **Frontend**: Vanilla JavaScript with WebSocket client
- **Database**: PostgreSQL 17 with timezone configuration
- **Image Processing**: PIL/Pillow with thread pool execution
- **Containerization**: Docker with multi-service orchestration

### Adding Features
- Upload service: Modify `upload.py` and `templates/upload.html`
- Display service: Modify `display.py` and `templates/display.html`
- Database: Update `init-db/init.sql` schema

## Troubleshooting

### Common Issues
```bash
# Check container status
docker-compose ps
# View logs
docker-compose logs upload-server
docker-compose logs display-server
docker-compose logs postgres
# Restart services
docker-compose restart
# Reset database (WARNING: deletes all data)
docker-compose down -v
docker-compose up -d
```

### Network Issues
- Ensure ports 8000, 8001, 5432 are not blocked
- Check firewall settings for church network
- Verify docker-compose networking

## License

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
