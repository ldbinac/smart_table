# Smart Table

[中文](README.md) | English

A smart multi-dimensional table system based on Vue 3 + TypeScript + Pinia, supporting both pure frontend (IndexedDB) and backend (PostgreSQL/SQLite) deployment modes, similar to Airtable or Lark Base.

## ✨ Features

### 🎯 Core Features

- **Base Management** - Create, edit, delete, star multi-dimensional tables with member management and sharing
- **Table Management** - Support multiple tables with drag-sort, rename, delete, and duplicate
- **Field Management** - Support **26 field types** with configuration, sorting, visibility control, and default values
- **Record Management** - CRUD operations, batch actions, detail drawer, and change history tracking
- **View Management** - **6 view types** with filtering, sorting, grouping, view switching, and column freezing

### 📝 Supported Field Types (26 Types)

| Category            | Field Type       | Description                                                         | Status |
| ------------------- | ---------------- | ------------------------------------------------------------------- | ------ |
| **Text Types**      | Single Line Text | Short text input with validation rules                              | ✅      |
| **Text Types**      | Long Text        | Long text/paragraph input with multi-line editing                   | ✅      |
| **Text Types**      | Rich Text        | HTML rich text editor with formatting support                       | ✅      |
| **Numeric Types**   | Number           | Integer/decimal with formatting (number/currency/percent)           | ✅      |
| **Date Types**      | Date             | Date picker supporting multiple date formats                        | ✅      |
| **Date Types**      | Date Time        | DateTime picker accurate to seconds                                 | ✅      |
| **Selection Types** | Single Select    | Dropdown single select with custom options and colors               | ✅      |
| **Selection Types** | Multi Select     | Tag-style multi select with custom options                          | ✅      |
| **Selection Types** | Checkbox         | Boolean toggle                                                      | ✅      |
| **People Types**    | Member           | User selection with current user default value                      | ✅      |
| **Contact Types**   | Phone            | Phone number input and formatted display                            | ✅      |
| **Contact Types**   | Email            | Email address input and validation                                  | ✅      |
| **Contact Types**   | URL              | URL link with click-to-navigate                                     | ✅      |
| **Media Types**     | Attachment       | File upload/download with image preview and thumbnails              | ✅      |
| **Computed Types**  | Formula          | 43 built-in functions with field references and nested calculations | ✅      |
| **Relation Types**  | Link             | Table relationships supporting one-to-one/one-to-many/many-to-many  | ✅      |
| **Lookup Types**    | Lookup           | Cross-table queries with aggregation (sum/avg/count/etc.)           | ✅      |
| **System Types**    | Created By       | Auto-record record creator                                          | ✅      |
| **System Types**    | Created Time     | Auto-record creation timestamp                                      | ✅      |
| **System Types**    | Updated By       | Auto-record last modifier                                           | ✅      |
| **System Types**    | Updated Time     | Auto-record last modification time                                  | ✅      |
| **System Types**    | Auto Number      | Auto-increment with prefix/suffix/date format/padding               | ✅      |
| **Others**          | Rating           | Star rating component                                               | ✅      |
| **Others**          | Progress         | Progress bar/percentage display                                     | ✅      |

### 🎨 Supported View Types (6 Types)

| View Type         | Description                                                            | Status |
| ----------------- | ---------------------------------------------------------------------- | ------ |
| **Table View**    | Classic table display with virtual scroll, column freeze, field filter | ✅      |
| **Kanban View**   | Card-based display with drag-sort and grouping                         | ✅      |
| **Calendar View** | Time-based display grouped by date                                     | ✅      |
| **Gantt View**    | Project timeline display with task dependencies                        | ✅      |
| **Form View**     | Data collection form with public sharing and customization             | ✅      |
| **Gallery View**  | Image card grid display for media content                              | ✅      |

### 🚀 Advanced Features

#### Data Processing

- **Data Filtering** - Multi-condition combined filtering with AND/OR logic, 20+ operators
- **Data Sorting** - Multi-field sorting with ascending/descending order, drag to adjust priority
- **Data Grouping** - Group by field with multi-level grouping (up to 3 levels), group statistics
- **Formula Engine** - **43 built-in functions** for math, text, date, logic, and statistics
- **Data Import** - Support Excel, CSV, JSON formats with multi-sheet, can import to create new tables
- **Data Export** - Support Excel, CSV, JSON formats with custom field selection

#### Collaboration & Sharing

- **Base Sharing** - Base-level sharing with link sharing and permission control
- **Form Sharing** - Form view public sharing with submission options configuration
- **Dashboard Sharing** - Dashboard public sharing with real-time data display
- **Member Management** - Base-level member list, add members, role assignment
- **Real-time Collaboration** - WebSocket-based multi-user real-time collaboration (optional)
  - Online presence display
  - View sync (scroll position, view switching)
  - Cell locking (prevent conflict editing)
  - Conflict detection & resolution (optimistic locking)
  - Offline queue (auto-cache on disconnect, auto-replay on reconnect)
  - Graceful degradation (auto-switch to normal mode when unavailable)

#### Permissions & Security

- **User Authentication** - JWT Token authentication with refresh token, email verification, password reset
- **Role-Based Access Control (RBAC)**:
  - Owner - Full control permissions
  - Admin - Management permissions (except deletion)
  - Editor - Edit permissions
  - Commenter - Comment and view permissions
  - Viewer - Read-only permissions
- **Security Protection** - XSS protection, CSRF protection, security headers, API rate limiting, file upload validation
- **Operation Logs** - Complete operation audit logs

#### User Experience

- **Drag Sorting** - Drag to sort tables, fields, views, Kanban cards
- **Star Feature** - Quick access to frequently used tables and dashboards
- **Search Feature** - Quick search for table names and record content
- **Element Plus Icons** - Unified icon system for visual consistency
- **Keyboard Shortcuts** - Common operation keyboard shortcuts

#### Dashboard System

- **Multiple Chart Components** - Number cards, clock, date, KPI cards, marquee, real-time charts, etc.
- **Dashboard Templates** - Save and reuse dashboard configurations as templates
- **Grid Layout** - Flexible grid layout system with customizable rows/columns
- **Real-time Data** - Real-time data updates and dynamic charts
- **Sharing Feature** - Dashboard public sharing with embed support for external websites

#### Email System (Optional)

- **SMTP Configuration** - Custom SMTP server support
- **Email Templates** - Customizable email templates (registration verification, password reset, etc.)
- **Email Queue** - Async email sending queue with retry mechanism
- **Email Logs** - Complete email sending logs and statistics
- **Admin Panel** - Email configuration management and monitoring interface

## 📸 Feature Preview

| Feature       | Preview                                         | Feature       | Preview                                         |
| ------------- | ----------------------------------------------- | ------------- | ----------------------------------------------- |
| Login         | ![](./doc/img/login.png)                        | Register      | ![](./doc/img/register.png)                     |
| Home          | ![Home](./doc/img/home.jpeg)                    | All Home      | ![Home2](./doc/img/home-all.jpeg)               |
| Table View    | ![Table View](./doc/img/TableView.jpeg)         | Grouped Table | ![Grouped Table](./doc/img/TableViewGroup.jpeg) |
| Table Fields  | ![Table Fields](./doc/img/TableViewFields.jpeg) | Kanban View   | ![Kanban View](./doc/img/KanbanView.jpeg)       |
| Calendar View | ![Calendar View](./doc/img/CalendarView.jpeg)   | Gantt View    | ![Gantt View](./doc/img/GanttView.jpeg)         |
| Form View     | ![Form View](./doc/img/FormView.jpeg)           | Dashboard     | ![Dashboard](./doc/img/Dashboard.jpeg)          |
| Sharing       | ![Sharing](./doc/img/sharing.png)               | -             | -                                               |

## 🛠️ Tech Stack

### Frontend Tech Stack

| Category             | Technology              | Version         | Description                           |
| -------------------- | ----------------------- | --------------- | ------------------------------------- |
| Frontend Framework   | Vue 3                   | ^3.5.30         | Composition API                       |
| Language             | TypeScript              | \~5.9.3         | Type safety                           |
| State Management     | Pinia                   | ^2.3.1          | Lightweight state management          |
| Router               | Vue Router              | ^4.6.4          | SPA routing                           |
| UI Component Library | Element Plus            | ^2.13.6         | Enterprise UI components              |
| Table Component      | vxe-table               | ^4.18.7         | High-performance virtual scroll table |
| Charts               | echarts + vue-echarts   | ^5.6.0 / ^6.7.3 | Data visualization                    |
| Date Processing      | dayjs                   | ^1.11.20        | Lightweight date library              |
| Drag Sorting         | sortablejs              | ^1.15.7         | Drag functionality                    |
| HTTP Client          | axios                   | ^1.14.0         | HTTP requests                         |
| Local Database       | Dexie                   | ^3.2.7          | IndexedDB wrapper                     |
| WebSocket            | socket.io-client        | ^4.8.3          | Real-time communication               |
| Utilities            | lodash-es, @vueuse/core | -               | Utility function sets                 |
| Rich Text            | dompurify               | ^3.4.0          | XSS protection                        |
| Spreadsheet          | xlsx                    | ^0.18.5         | Excel parsing/generation              |
| Build Tool           | Vite                    | ^8.0.1          | Ultra-fast build tool                 |
| Testing              | Vitest                  | ^3.2.4          | Unit testing                          |

### Backend Tech Stack (Optional)

| Category            | Technology                       | Version               | Description                   |
| ------------------- | -------------------------------- | --------------------- | ----------------------------- |
| Framework           | Flask                            | 3.0.0                 | Python Web framework          |
| Database            | SQLite (Default) / PostgreSQL    | 3.x / 16+             | Relational database           |
| ORM                 | SQLAlchemy                       | 2.0.23                | Python ORM                    |
| Database Migration  | Alembic (Flask-Migrate)          | 4.0.5                 | Database version management   |
| Authentication      | JWT (Flask-JWT-Extended)         | 4.6.0                 | Token authentication          |
| Password Encryption | Flask-Bcrypt, bcrypt             | 1.0.1 / 4.1.2         | Password hashing              |
| Form Validation     | Flask-WTF                        | 1.2.1                 | CSRF protection               |
| CORS                | Flask-CORS                       | 4.0.0                 | Cross-origin support          |
| Caching             | Flask-Caching (+ Redis Optional) | 2.1.0                 | Caching acceleration          |
| WebSocket           | Flask-SocketIO                   | 5.3.6                 | Real-time communication       |
| Async Support       | eventlet                         | 0.36.1                | Async processing              |
| Data Serialization  | marshmallow                      | 3.20.1                | Data validation/serialization |
| Import/Export       | pandas, openpyxl, xlrd           | 2.1.4 / 3.1.2 / 2.0.1 | Data processing               |
| Image Processing    | Pillow                           | 10.4.0                | Image thumbnails              |
| Object Storage      | MinIO (Optional)                 | -                     | File object storage           |
| Encryption          | cryptography                     | 42.0.5                | Encryption algorithms         |
| API Documentation   | Flasgger                         | 0.9.7b2               | Swagger UI                    |
| WSGI Server         | Gunicorn                         | 21.2.0                | Production server             |
| Deployment          | Docker, Nginx                    | -                     | Containerized deployment      |

### Data Storage Options

| Mode                   | Technology         | Description                                                                                        |
| ---------------------- | ------------------ | -------------------------------------------------------------------------------------------------- |
| **Pure Frontend Mode** | Dexie (IndexedDB)  | Data stored locally in browser, no server required, suitable for personal use or offline scenarios |
| **Backend Mode**       | SQLite + Flask     | Default uses SQLite, lightweight without additional database installation                          |
| **Production Mode**    | PostgreSQL + Flask | Supports PostgreSQL, suitable for multi-user concurrent access and production environments         |

## 🚀 Quick Start

### Requirements

- Node.js >= 18
- npm >= 9
- Python >= 3.9 (Only for backend mode)

### One-click Start (Recommended)

Use the startup script in the project root:

```bash
# Windows PowerShell
.\start.ps1

# Linux/macOS
./start.sh
```

The script will automatically:

1. Install frontend dependencies and start dev server (port 5173)
2. Install backend dependencies and start Flask server (port 5000)
3. Open browser at <http://localhost:5173>

### Frontend Development

#### Install Dependencies

```bash
cd smart-table
npm install
```

#### Development Mode

```bash
npm run dev
```

Visit <http://localhost:5173>

#### Build for Production

```bash
npm run build
```

#### Preview Production Build

```bash
npm run preview
```

#### Run Tests

```bash
# Run all tests
npm run test

# Watch mode (for development)
npm run test:watch

# Generate test coverage report
npm run test:coverage
```

### Backend Service (Optional)

#### Using Docker Compose (Recommended)

```bash
cd smarttable-backend

# Copy environment variables
cp .env.example .env
# Edit .env file to configure database connection (default uses SQLite)

# Start all services (SQLite mode)
docker-compose up -d

# Or use PostgreSQL + Redis (for production)
docker-compose -f docker-compose.dev.yml up -d

# Run database migrations
docker-compose exec backend flask db upgrade

# View logs
docker-compose logs -f backend

# Access API documentation
# http://localhost:5000/api/docs  (Swagger UI)
# http://localhost:5000/api/apidoc  (ReDoc)
```

#### Local Development

```bash
cd smarttable-backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env
# Default uses SQLite, no need to modify DATABASE_URL

# Initialize database
flask db upgrade

# Start development server (real-time collaboration disabled by default)
flask run --reload

# Or use run.py to start (supports more options)
python run.py

# Enable real-time collaboration
python run.py --enable-realtime
# Or use short flag
python run.py -r
```

#### Backend Features

✅ **Default Database**: SQLite (lightweight, no additional installation required)\
✅ **Optional Database**: PostgreSQL (configurable via `DATABASE_URL` environment variable)\
✅ **Authentication**: JWT Token authentication with refresh token, email verification\
✅ **Permission Management**: Role-based access control (RBAC)\
✅ **Database Migration**: Alembic migration tool\
✅ **API Documentation**: Complete Swagger/OpenAPI documentation (Flasgger)\
✅ **Real-time Collaboration**: Optional WebSocket real-time collaboration (enable via `--enable-realtime`)\
✅ **Email System**: Optional SMTP email sending\
✅ **Object Storage**: Optional MinIO file storage\
✅ **Security Protection**: XSS protection, rate limiting, security headers

## 📁 Project Structure

### Frontend Project Structure

```
smart-table/
├── src/
│   ├── assets/                    # Static assets
│   │   └── styles/               # SCSS style files (global styles, variables, mixins)
│   ├── components/                # Vue components
│   │   ├── common/               # Common components
│   │   │   ├── AppHeader.vue     # App header (navigation, user info, collaboration status)
│   │   │   ├── AppSidebar.vue    # App sidebar
│   │   │   ├── Toast.vue         # Message toast
│   │   │   ├── Loading.vue       # Loading state
│   │   │   └── ...
│   │   ├── collaboration/        # Collaboration components
│   │   │   ├── OnlineUsers.vue           # Online users list
│   │   │   ├── CellEditingIndicator.vue  # Cell editing indicator
│   │   │   ├── ConflictDialog.vue        # Conflict resolution dialog
│   │   │   ├── ConnectionStatusBar.vue   # Connection status bar
│   │   │   └── CollaborationToast.vue    # Collaboration toast messages
│   │   ├── dialogs/              # Dialog components
│   │   │   ├── FieldDialog.vue          # Field configuration dialog
│   │   │   ├── FilterDialog.vue         # Filter dialog
│   │   │   ├── SortDialog.vue           # Sort dialog
│   │   │   ├── GroupDialog.vue          # Group dialog
│   │   │   ├── ImportDialog.vue         # Import dialog
│   │   │   ├── ExportDialog.vue         # Export dialog
│   │   │   ├── RecordDetailDrawer.vue   # Record detail drawer
│   │   │   ├── RecordHistoryDrawer.vue  # Change history drawer
│   │   │   ├── ExcelImportCreateDialog.vue  # Excel import create table
│   │   │   └── ...
│   │   ├── fields/               # 26 field type components
│   │   │   ├── SingleLineTextField.vue   # Single line text
│   │   │   ├── LongTextField.vue         # Long text
│   │   │   ├── RichTextField.vue         # Rich text
│   │   │   ├── NumberField.vue           # Number
│   │   │   ├── DateField.vue             # Date
│   │   │   ├── DateTimeField.vue         # DateTime ⭐
│   │   │   ├── SingleSelectField.vue     # Single select
│   │   │   ├── MultiSelectField.vue      # Multi select
│   │   │   ├── CheckboxField.vue         # Checkbox
│   │   │   ├── MemberField.vue           # Member
│   │   │   ├── PhoneField.vue            # Phone
│   │   │   ├── EmailField.vue            # Email
│   │   │   ├── URLField.vue              # URL link
│   │   │   ├── AttachmentField.vue       # Attachment
│   │   │   ├── FormulaField.vue          # Formula
│   │   │   ├── LinkField.vue             # Link
│   │   │   ├── LookupField.vue           # Lookup
│   │   │   ├── CreatedByField.vue        # Created By
│   │   │   ├── CreatedTimeField.vue      # Created Time
│   │   │   ├── UpdatedByField.vue        # Updated By
│   │   │   ├── UpdatedTimeField.vue      # Updated Time
│   │   │   ├── AutoNumberField.vue       # Auto Number ⭐
│   │   │   ├── RatingField.vue           # Rating
│   │   │   ├── ProgressField.vue         # Progress
│   │   │   ├── FieldComponentFactory.vue # Field factory
│   │   │   └── FieldConfigPanel.vue      # Field config panel
│   │   ├── filters/              # Filter components
│   │   │   ├── FilterPanel.vue           # Filter panel
│   │   │   ├── FilterCondition.vue       # Filter condition
│   │   │   └── FilterValueInput.vue      # Filter value input
│   │   ├── groups/               # Group components
│   │   │   ├── GroupPanel.vue            # Group panel
│   │   │   └── GroupedTableView.vue      # Grouped table view
│   │   ├── sorts/                # Sort components
│   │   │   └── SortPanel.vue            # Sort panel
│   │   ├── views/                # 6 view type components
│   │   │   ├── TableView/                # Table view
│   │   │   │   ├── TableView.vue         # Main view
│   │   │   │   ├── TableHeader.vue       # Table header
│   │   │   │   ├── TableRow.vue          # Row component
│   │   │   │   └── TableCell.vue         # Cell component
│   │   │   ├── KanbanView/               # Kanban view
│   │   │   │   ├── KanbanView.vue        # Main view
│   │   │   │   ├── KanbanColumn.vue      # Kanban column
│   │   │   │   └── KanbanCard.vue        # Kanban card
│   │   │   ├── CalendarView/             # Calendar view
│   │   │   ├── GanttView/                # Gantt view
│   │   │   ├── FormView/                 # Form view
│   │   │   │   ├── FormView.vue          # Main view
│   │   │   │   ├── FormViewConfig.vue    # Form config
│   │   │   │   └── FormShareDialog.vue   # Form share
│   │   │   ├── GalleryView/              # Gallery view
│   │   │   └── ViewSwitcher.vue          # View switcher
│   │   ├── dashboard/            # Dashboard components
│   │   │   ├── KpiWidget.vue             # KPI card
│   │   │   ├── ClockWidget.vue           # Clock widget
│   │   │   ├── DateWidget.vue            # Date widget
│   │   │   ├── RealtimeChartWidget.vue   # Real-time chart
│   │   │   ├── MarqueeWidget.vue         # Marquee widget
│   │   │   └── index.ts
│   │   ├── auth/                 # Auth components
│   │   │   ├── LoginForm.vue             # Login form
│   │   │   └── RegisterForm.vue          # Register form
│   │   └── base/                 # Base components
│   │       ├── MemberList.vue            # Member list
│   │       └── AddMemberDialog.vue       # Add member dialog
│   ├── composables/                # Composable functions
│   │   ├── useEntityOperations.ts        # Entity operations (CRUD)
│   │   └── useRealtimeCollaboration.ts   # Real-time collaboration
│   ├── db/                         # Database layer (IndexedDB)
│   │   ├── services/               # Data services
│   │   │   ├── baseService.ts             # Base service
│   │   │   ├── tableService.ts            # Table service
│   │   │   ├── fieldService.ts            # Field service
│   │   │   ├── recordService.ts           # Record service
│   │   │   ├── viewService.ts             # View service
│   │   │   ├── dashboardService.ts        # Dashboard service
│   │   │   ├── attachmentService.ts       # Attachment service
│   │   │   ├── templateService.ts         # Template service
│   │   │   └── dashboardShareService.ts   # Dashboard share service
│   │   ├── schema.ts               # Dexie database definition
│   │   └── __tests__/              # Test files
│   ├── layouts/                    # Layout components
│   │   ├── MainLayout.vue          # Main layout
│   │   └── BlankLayout.vue         # Blank layout
│   ├── router/                     # Vue Router config
│   │   ├── index.ts                # Route definitions
│   │   └── guards.ts               # Route guards
│   ├── services/api/               # API service layer
│   │   ├── authService.ts          # Auth API
│   │   ├── authApiService.ts       # Auth API service
│   │   ├── baseApiService.ts       # Base API
│   │   ├── tableApiService.ts      # Table API
│   │   ├── fieldApiService.ts      # Field API
│   │   ├── recordApiService.ts     # Record API
│   │   ├── viewApiService.ts       # View API
│   │   ├── dashboardApiService.ts  # Dashboard API
│   │   ├── attachmentApiService.ts # Attachment API
│   │   ├── shareApiService.ts      # Share API
│   │   ├── importExportApiService.ts # Import/Export API
│   │   ├── adminApiService.ts      # Admin API
│   │   ├── emailApiService.ts      # Email API
│   │   └── linkApiService.ts       # Link API
│   ├── services/realtime/          # Real-time collaboration service layer
│   │   ├── socketClient.ts         # Socket.IO client
│   │   ├── eventTypes.ts           # Event type definitions
│   │   └── eventEmitter.ts         # Event bus
│   ├── stores/                     # Pinia state management
│   │   ├── authStore.ts            # Auth state
│   │   ├── auth/authStore.ts       # Auth state (new version)
│   │   ├── baseStore.ts            # Base state
│   │   ├── tableStore.ts           # Table state
│   │   ├── viewStore.ts            # View state
│   │   ├── collaborationStore.ts   # Collaboration state
│   │   ├── adminStore.ts           # Admin state
│   │   ├── settingsStore.ts        # Settings state
│   │   ├── loadingStore.ts         # Loading state
│   │   ├── userCacheStore.ts       # User cache
│   │   ├── keyboardShortcuts.ts    # Keyboard shortcuts config
│   │   └── theme.ts                # Theme config
│   ├── types/                      # TypeScript type definitions
│   │   ├── fields.ts               # Field type definitions
│   │   ├── views.ts                # View type definitions
│   │   ├── filters.ts              # Filter type definitions
│   │   ├── attachment.ts           # Attachment type definitions
│   │   └── link.ts                 # Link type definitions
│   ├── utils/                      # Utility functions
│   │   ├── formula/                # Formula engine
│   │   │   ├── engine.ts           # Formula parser engine
│   │   │   ├── functions.ts        # 43 built-in functions
│   │   │   └── index.ts
│   │   ├── export/                 # Export functionality
│   │   ├── attachment/             # Attachment utilities
│   │   │   ├── validators.ts       # Validators
│   │   │   ├── thumbnail.ts        # Thumbnail generation
│   │   │   └── errors.ts           # Error handling
│   │   ├── filter.ts               # Filter logic
│   │   ├── sort.ts                 # Sort logic
│   │   ├── group.ts                # Group logic
│   │   ├── validation.ts           # Data validation
│   │   ├── importExport.ts         # Import/export logic
│   │   ├── cache.ts                # Cache utilities
│   │   ├── debounce.ts             # Debounce function
│   │   ├── helpers.ts              # General helper functions
│   │   ├── history.ts              # History records
│   │   ├── id.ts                   # ID generation
│   │   ├── logger.ts               # Logger utilities
│   │   ├── message.ts              # Message utilities
│   │   ├── performance.ts          # Performance optimization
│   │   ├── sanitize.ts             # HTML sanitization
│   │   ├── tableTemplates.ts       # Table templates
│   │   ├── templateGenerator.ts    # Template generator
│   │   ├── recordValueSerializer.ts # Record value serializer
│   │   ├── viewConfigSerializer.ts # View config serializer
│   │   ├── dashboardDataProcessor.ts # Dashboard data processor
│   │   ├── dashboardLayoutEngine.ts  # Dashboard layout engine
│   │   └── dashboardWidgetRegistry.ts # Dashboard widget registry
│   ├── views/                      # Page views
│   │   ├── Home.vue                # Home page
│   │   ├── Base.vue                 # Base main page
│   │   ├── Dashboard.vue            # Dashboard page
│   │   ├── DashboardShare.vue       # Dashboard share page
│   │   ├── FormShare.vue            # Form share page
│   │   ├── BaseShare.vue            # Base share page
│   │   ├── Settings.vue             # Settings page
│   │   ├── auth/                   # Auth pages
│   │   │   ├── Login.vue           # Login
│   │   │   ├── Register.vue        # Register
│   │   │   ├── ForgotPassword.vue  # Forgot password
│   │   │   ├── ResetPassword.vue   # Reset password
│   │   │   └── VerifyEmail.vue     # Email verification
│   │   ├── admin/                  # Admin panel
│   │   │   ├── UserManagement.vue  # User management
│   │   │   ├── SystemSettings.vue  # System settings
│   │   │   ├── EmailTemplates.vue  # Email templates
│   │   │   ├── EmailLogs.vue       # Email logs
│   │   │   ├── EmailStats.vue      # Email statistics
│   │   │   └── OperationLogs.vue   # Operation logs
│   │   └── base/                   # Base related
│   │       └── MemberManagement.vue # Member management
│   ├── App.vue                     # Root component
│   ├── main.ts                     # Entry file
│   ├── style.css                   # Global styles
│   ├── auto-imports.d.ts           # Auto-import types
│   └── components.d.ts             # Component types
├── tests/                          # Test directory
├── package.json
├── vite.config.ts                  # Vite config
├── tsconfig.json                   # TypeScript config
├── vitest.config.ts                # Vitest config
└── README.md
```

### Backend Project Structure

```
smarttable-backend/
├── app/
│   ├── __init__.py                 # Application factory
│   ├── config.py                   # Configuration
│   ├── extensions.py               # Extensions initialization
│   ├── db_types.py                 # Database type definitions
│   ├── models/                     # Data models
│   │   ├── user.py                 # User model
│   │   ├── base.py                 # Base model
│   │   ├── table.py                # Table model
│   │   ├── field.py                # Field model
│   │   ├── record.py               # Record model
│   │   ├── view.py                 # View model
│   │   ├── dashboard.py            # Dashboard model
│   │   ├── dashboard_share.py      # Dashboard share model
│   │   ├── attachment.py           # Attachment model
│   │   ├── base_share.py           # Base share model
│   │   ├── form_share.py           # Form share model
│   │   ├── form_submission.py      # Form submission model
│   │   ├── link_relation.py        # Link relation model
│   │   ├── collaboration_session.py # Collaboration session model
│   │   ├── email_log.py            # Email log model
│   │   ├── email_template.py       # Email template model
│   │   ├── operation_history.py    # Operation history model
│   │   ├── log.py                  # Log model
│   │   └── config.py               # Config model
│   ├── services/                   # Business logic layer
│   │   ├── auth_service.py         # Auth service
│   │   ├── base_service.py         # Base service
│   │   ├── table_service.py        # Table service
│   │   ├── field_service.py        # Field service
│   │   ├── record_service.py       # Record service
│   │   ├── view_service.py         # View service
│   │   ├── formula_service.py      # Formula service
│   │   ├── dashboard_service.py    # Dashboard service
│   │   ├── dashboard_share_service.py # Dashboard share service
│   │   ├── attachment_service.py   # Attachment service
│   │   ├── collaboration_service.py # Collaboration service
│   │   ├── share_service.py        # Share service
│   │   ├── form_share_service.py   # Form share service
│   │   ├── permission_service.py   # Permission service
│   │   ├── import_export_service.py # Import/Export service
│   │   ├── link_service.py        # Link service
│   │   ├── admin_service.py       # Admin service
│   │   ├── email_sender_service.py # Email sender service
│   │   ├── email_config_service.py # Email config service
│   │   ├── email_queue_service.py  # Email queue service
│   │   ├── email_retry_service.py  # Email retry service
│   │   └── email_template_service.py # Email template service
│   ├── routes/                     # Routes layer (RESTful API)
│   │   ├── auth.py                 # Auth routes (/api/auth/*)
│   │   ├── auth_captcha.py         # Captcha routes (/api/auth/captcha)
│   │   ├── bases.py                # Base routes (/api/bases/*)
│   │   ├── tables.py               # Table routes (/api/bases/{base_id}/tables/*)
│   │   ├── fields.py               # Field routes (/api/fields/*)
│   │   ├── records.py              # Record routes (/api/records/*)
│   │   ├── views.py                # View routes (/api/views/*)
│   │   ├── dashboards.py           # Dashboard routes (/api/dashboards/*)
│   │   ├── dashboards_share.py     # Dashboard share routes
│   │   ├── attachments.py          # Attachment routes (/api/attachments/*)
│   │   ├── shares.py               # Share routes (/api/shares/*)
│   │   ├── form_shares.py          # Form share routes (/api/form-shares/*)
│   │   ├── import_export.py        # Import/Export routes (/api/import-export/*)
│   │   ├── email.py                # Email routes (/api/email/*)
│   │   ├── admin.py                # Admin routes (/api/admin/*)
│   │   ├── users.py                # User routes (/api/users/*)
│   │   ├── realtime.py             # Real-time collaboration status API (/api/realtime/*)
│   │   └── socketio_events.py      # Socket.IO event handlers
│   ├── schemas/                    # Data validation schemas
│   │   ├── user_schema.py          # User validation
│   │   ├── record_schema.py        # Record validation
│   │   └── admin_schema.py         # Admin validation
│   ├── utils/                      # Utility modules
│   │   ├── captcha.py              # Captcha generation
│   │   ├── constants.py            # Constants definition
│   │   ├── decorators.py           # Decorators
│   │   ├── exception_handler.py    # Exception handling
│   │   ├── response.py             # Response formatting
│   │   ├── validators.py           # Validators
│   │   └── init_email_templates.py # Initialize email templates
│   ├── errors/                     # Error handling
│   │   └── handlers.py             # Error handlers
│   ├── middleware/                  # Middleware
│   │   └── security_headers.py     # Security headers
│   └── data/                       # Data files
│       └── default_email_templates.py # Default email templates
├── migrations/                     # Database migrations (Alembic)
│   ├── versions/                   # Migration versions
│   │   ├── 20250403_0001_initial_migration.py
│   │   ├── 20250405_0002_add_dashboard_is_default.py
│   │   ├── 20250406_0002_add_admin_management_models.py
│   │   ├── 20250406_0003_add_base_sharing.py
│   │   ├── 20250409_0004_add_link_relations.py
│   │   ├── 20250412_0005_add_form_share_tables.py
│   │   ├── 20250414_0006_add_email_tables.py
│   │   ├── 20250414_0007_add_user_email_verification.py
│   │   └── 20250416_0008_add_collaboration_sessions.py
│   ├── env.py                      # Migration environment
│   └── script.py.mako              # Migration script template
├── tests/                          # Test directory
│   ├── conftest.py                 # Test configuration
│   ├── test_auth.py                # Auth tests
│   ├── test_base.py                # Base tests
│   ├── test_table.py               # Table tests
│   ├── test_field.py               # Field tests
│   ├── test_record.py              # Record tests
│   ├── test_view.py                # View tests
│   ├── test_dashboard.py           # Dashboard tests
│   ├── test_attachment.py          # Attachment tests
│   ├── test_formula_service.py     # Formula service tests
│   ├── test_import_export.py       # Import/Export tests
│   ├── test_auto_number.py         # Auto number tests
│   ├── test_member_sharing.py      # Member sharing tests
│   ├── test_create_base.py         # Create Base tests
│   ├── test_realtime_enabled.py    # Real-time collaboration tests (enabled)
│   ├── test_realtime_disabled.py   # Real-time collaboration tests (disabled)
│   ├── test_logout_all.py          # Logout tests
│   ├── test_validators.py          # Validator tests
│   ├── test_startup_params.py      # Startup parameter tests
│   ├── test_email_integration.py   # Email integration tests
│   └── test_email_services.py      # Email service tests
├── requirements.txt                # Python dependencies
├── requirements-dev.txt            # Dev dependencies
├── requirements-minimal.txt        # Minimal dependencies
├── run.py                          # Application entry point
├── init_db.py                      # Database initialization
├── init_link_tables.py             # Link tables initialization
├── gunicorn.conf.py                # Gunicorn config
├── alembic.ini                     # Alembic config
├── Dockerfile                      # Docker image
├── Dockerfile.dev                  # Dev image
├── docker-compose.yml              # Docker compose (SQLite)
├── docker-compose.dev.yml          # Docker compose (PostgreSQL)
├── .env.example                    # Environment variables example
└── README.md
```

## 🗄️ Data Models

### Core Entity Relationships

```
User (User)
  ├── owns many Base (Multi-dimensional Tables)
  ├── is member of many Base (via BaseMember)
  └── has many OperationLog (Operation Logs)

Base (Multi-dimensional Table)
  ├── has many Table (Data Tables)
  ├── has many Dashboard (Dashboards)
  ├── has many BaseShare (Share Links)
  ├── has many BaseMember (Members)
  └── has many CollaborationSession (Collaboration Sessions)

Table (Data Table)
  ├── has many Field (Fields)
  ├── has many Record (Records)
  ├── has many View (Views)
  ├── has many LinkRelation (Link Relations)
  └── belongs to Base

Field (Field)
  ├── has options (field options)
  └── belongs to Table

Record (Record)
  ├── has many RecordHistory (Change History)
  ├── has values for each Field
  └── belongs to Table

View (View)
  ├── has filter/sort/group configs
  └── belongs to Table
```

### Main Model Descriptions

#### User

- User authentication info (username, email, password hash)
- Email verification status
- Role permissions (regular user/admin)
- Avatar and profile info

#### Base (Multi-dimensional Table)

- Base unit for multi-dimensional tables
- Support starring, custom icon and color
- Member management and permission control
- Sharing settings (public/private/password protected)

#### Table (Data Table)

- Contains field definitions and record data
- Support drag-sort, starring
- Relationship configuration

#### Field (Field)

- Define column types and properties
- Support 26 field types
- Rich field options (validation rules, default values, formatting, etc.)

#### Record (Record)

- Data row storing values for each field
- Support CRUD, batch operations
- Complete change history tracking

#### View (View)

- Data display method (6 view types)
- Independent filter, sort, group configurations
- View-level field control (hidden, freeze, width)

#### CollaborationSession

- Real-time collaboration session tracking
- Records user join/leave and active status
- Only used when real-time collaboration is enabled

## 🔢 Formula Engine

### Formula Usage Examples

```javascript
// Math calculation
{Unit Price} * {Quantity}

// Discount calculation
{Original Price} * (1 - {Discount})

// Conditional judgment (nested IF)
IF({Score} >= 90, "Excellent", IF({Score} >= 60, "Pass", "Fail"))

// Text concatenation
CONCAT({First Name}, {Last Name})

// Date calculation
DATEDIF({Start Date}, {End Date}, "D")

// Statistical calculation
SUMIF({Department}, "Sales", {Sales Amount})

// Lookup reference
LOOKUP({Related Table.Related Records}, {Target Field})
```

### Supported Functions (43 Total)

#### 📊 Math Functions (11)

| Function  | Description    | Example                   |
| --------- | -------------- | ------------------------- |
| `SUM`     | Sum            | `SUM({Field1}, {Field2})` |
| `AVG`     | Average        | `AVG({Score})`            |
| `MAX`     | Maximum        | `MAX({Age})`              |
| `MIN`     | Minimum        | `MIN({Price})`            |
| `ROUND`   | Round          | `ROUND({Value}, 2)`       |
| `CEILING` | Round up       | `CEILING({Value})`        |
| `FLOOR`   | Round down     | `FLOOR({Value})`          |
| `ABS`     | Absolute value | `ABS({Difference})`       |
| `MOD`     | Modulo         | `MOD({Value}, 2)`         |
| `POWER`   | Power          | `POWER({Base}, 2)`        |
| `SQRT`    | Square root    | `SQRT({Value})`           |

#### 📝 Text Functions (10)

| Function     | Description      | Example                            |
| ------------ | ---------------- | ---------------------------------- |
| `CONCAT`     | Concatenate text | `CONCAT({First}, {Last})`          |
| `LEFT`       | Left extract     | `LEFT({Text}, 3)`                  |
| `RIGHT`      | Right extract    | `RIGHT({Text}, 3)`                 |
| `LEN`        | Text length      | `LEN({Description})`               |
| `UPPER`      | To uppercase     | `UPPER({Text})`                    |
| `LOWER`      | To lowercase     | `LOWER({Text})`                    |
| `TRIM`       | Trim spaces      | `TRIM({Text})`                     |
| `SUBSTITUTE` | Replace text     | `SUBSTITUTE({Text}, "Old", "New")` |
| `REPLACE`    | Replace position | `REPLACE({Text}, 1, 3, "New")`     |
| `FIND`       | Find position    | `FIND("Substring", {Text})`        |

#### 📅 Date Functions (10)

| Function  | Description       | Example                        |
| --------- | ----------------- | ------------------------------ |
| `TODAY`   | Today's date      | `TODAY()`                      |
| `NOW`     | Current time      | `NOW()`                        |
| `YEAR`    | Extract year      | `YEAR({Date})`                 |
| `MONTH`   | Extract month     | `MONTH({Date})`                |
| `DAY`     | Extract day       | `DAY({Date})`                  |
| `HOUR`    | Extract hour      | `HOUR({Time})`                 |
| `MINUTE`  | Extract minute    | `MINUTE({Time})`               |
| `SECOND`  | Extract second    | `SECOND({Time})`               |
| `DATEDIF` | Date difference   | `DATEDIF({Start}, {End}, "D")` |
| `DATEADD` | Date add/subtract | `DATEADD({Date}, 7, "D")`      |

#### 🧠 Logic Functions (7)

| Function  | Description       | Example                            |
| --------- | ----------------- | ---------------------------------- |
| `IF`      | Conditional       | `IF({Condition}, "True", "False")` |
| `AND`     | Logical AND       | `AND({Cond1}, {Cond2})`            |
| `OR`      | Logical OR        | `OR({Cond1}, {Cond2})`             |
| `NOT`     | Logical NOT       | `NOT({Condition})`                 |
| `IFERROR` | Error handling    | `IFERROR({Formula}, "Default")`    |
| `IFS`     | Multi-condition   | `IFS({C1}, {V1}, {C2}, {V2})`      |
| `SWITCH`  | Multi-value match | `SWITCH({Field}, "A", 1, "B", 2)`  |

#### 📈 Statistical Functions (5)

| Function    | Description         | Example                                    |
| ----------- | ------------------- | ------------------------------------------ |
| `COUNT`     | Count               | `COUNT({Field})`                           |
| `COUNTA`    | Non-empty count     | `COUNTA({Field})`                          |
| `COUNTIF`   | Conditional count   | `COUNTIF({Field}, ">100")`                 |
| `SUMIF`     | Conditional sum     | `SUMIF({Category}, "A", {Amount})`         |
| `AVERAGEIF` | Conditional average | `AVERAGEIF({Department}, "R&D", {Salary})` |

## 🌐 RESTful API Endpoints

### API Basics

- **Base URL**: `http://localhost:5000/api`
- **Authentication**: Bearer Token (JWT)
- **Data Format**: JSON
- **API Documentation**:
  - Swagger UI: `http://localhost:5000/apidocs`

    <br />

## ⚡ Real-time Collaboration Configuration

Real-time collaboration is based on WebSocket (Socket.IO), supporting multiple users editing the same table simultaneously.

### Startup Parameters

```bash
# Enable real-time collaboration
python run.py --enable-realtime
# Or use short flag
python run.py -r

# Disable real-time collaboration (default behavior)
python run.py
```

### Environment Variables

```env
# Enable real-time collaboration
ENABLE_REALTIME=true

# SocketIO message queue (recommended when using Redis, for multi-process deployment)
SOCKETIO_MESSAGE_QUEUE=redis://localhost:6379/1

# SocketIO heartbeat configuration
SOCKETIO_PING_TIMEOUT=60
SOCKETIO_PING_INTERVAL=25
```

### Docker Deployment

Add to `docker-compose.yml` or `.env` file:

```yaml
environment:
  - ENABLE_REALTIME=true
  - SOCKETIO_MESSAGE_QUEUE=redis://redis:6379/1
```

### Feature Overview

| Feature                  | Description                                                                      |
| ------------------------ | -------------------------------------------------------------------------------- |
| **Online Presence**      | Display users currently editing the same table with cursor positions             |
| **View Sync**            | Real-time sync of other users' view switching and scroll positions               |
| **Cell Locking**         | Automatically lock cells being edited to prevent conflicts                       |
| **Conflict Detection**   | Optimistic locking-based conflict detection, returns 409 Conflict status code    |
| **Offline Queue**        | Operations auto-cached when disconnected, auto-replayed in order on reconnection |
| **Graceful Degradation** | Auto-degrade to normal HTTP polling when WebSocket unavailable                   |

### Socket.IO Events

| Event Category      | Event Name                        | Description                        |
| ------------------- | --------------------------------- | ---------------------------------- |
| **Room Management** | `room:join` / `room:leave`        | Join/leave collaboration room      |
| **Presence**        | `presence:view_changed`           | View switch notification           |
| <br />              | `presence:cell_selected`          | Cell selection notification        |
| <br />              | `presence:user_joined`            | User joined notification           |
| <br />              | `presence:user_left`              | User left notification             |
| **Cell Locking**    | `lock:acquire` / `lock:release`   | Acquire/release cell lock          |
| <br />              | `lock:acquired` / `lock:released` | Lock/unlock broadcast notification |
| **Data Sync**       | `data:record_updated`             | Record update push                 |
| <br />              | `data:record_created`             | Record creation push               |
| <br />              | `data:record_deleted`             | Record deletion push               |
| <br />              | `data:field_updated`              | Field update push                  |
| <br />              | `data:view_updated`               | View update push                   |
| <br />              | `data:table_updated`              | Table update push                  |
| <br />              | `data:table_created`              | Table creation push                |
| <br />              | `data:table_deleted`              | Table deletion push                |

## 🐳 Docker Deployment

### Quick Deploy (One-click Start)

```bash
# Clone repository
git clone <repository-url>
cd smart-table-spec

# Copy environment variables
cp .env.example .env
# Edit .env file, modify configuration as needed

# Start all services (frontend + backend + database)
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

Access URLs:

- Frontend: <http://localhost>
- Backend API: <http://localhost:5000/api>
- API Docs: <http://localhost:5000/api/docs>

### Production Deployment (PostgreSQL + Redis)

```bash
# Use production configuration
docker-compose -f docker-compose.full.yml up -d

# Or start separately
docker-compose -f docker-compose.dev.yml up -d
```

### Docker Compose Service Architecture

```
smart-table-spec/
├── docker-compose.yml              # Development (SQLite)
├── docker-compose.full.yml         # Production (PostgreSQL + Redis + MinIO)
├── docker-compose.dev.yml          # Development (PostgreSQL + Redis)
├── Dockerfile                      # Frontend build + Nginx
├── smarttable-backend/
│   ├── Dockerfile                  # Backend application
│   └── docker-compose.yml          # Backend standalone orchestration
└── docker/
    ├── nginx/
    │   └── nginx.conf              # Nginx configuration
    └── supervisor/
        └── supervisord.conf        # Process manager configuration
```

### Environment Variable Configuration

See [.env.example](.env.example) and [smarttable-backend/.env.example](smarttable-backend/.env.example)

Key configuration items:

| Variable          | Description                    | Default                   | Required                  |
| ----------------- | ------------------------------ | ------------------------- | ------------------------- |
| `SECRET_KEY`      | Flask secret key               | -                         | ✅ Production              |
| `JWT_SECRET_KEY`  | JWT secret key                 | -                         | ✅ Production              |
| `DATABASE_URL`    | Database connection            | sqlite:///smarttable.db   | ❌                         |
| `REDIS_URL`       | Redis address                  | redis\://localhost:6379/0 | ❌                         |
| `ENABLE_REALTIME` | Enable real-time collaboration | false                     | ❌                         |
| `MAIL_SERVER`     | SMTP server                    | -                         | ❌ (email feature needed)  |
| `MINIO_ENDPOINT`  | MinIO address                  | -                         | ❌ (object storage needed) |

## 🌍 Browser Support

| Browser | Minimum Version |
| ------- | --------------- |
| Chrome  | >= 90           |
| Firefox | >= 88           |
| Safari  | >= 14           |
| Edge    | >= 90           |

> 💡 **Tip**: Recommended to use the latest version of Chrome or Edge for best experience

## 📋 Development Roadmap & Version History

### v1.2.0 - Latest Version (In Development)

#### Recent 10 Days Important Updates (2026-04-16 \~ 2026-04-26)

##### ✨ New Features

- **⭐ DateTime Field** - New DateTimeField supporting combined date and time selection
- **⭐ Text Field Refactoring** - Split original "text" field into three independent types:
  - Single Line Text - Short text input
  - Long Text - Long text/paragraph input
  - Rich Text - HTML formatted text editor
- **⭐ Auto Number Field** - New AutoNumberField supporting:
  - Custom prefix/suffix
  - Date prefix (YYYYMMDD, YYYYMM formats)
  - Zero padding (specified digits)
  - Sequence auto-increment
- **⭐ Excel Import Create Table** - New feature to import from Excel and create new data tables directly
- **⭐ API Documentation System** - Integrated Flasgger providing complete Swagger/OpenAPI documentation
  - Detailed docs for all API endpoints
  - Swagger UI interactive interface (`/api/docs`)
  - ReDoc documentation interface (`/api/apidoc`)
- **⭐ Element Plus Icon System** - Comprehensive replacement of custom SVG icons with Element Plus icon components
  - Unified visual style
  - Better maintainability
- **⭐ Member Selection Component** - New MemberSelect component supporting:
  - User search and selection
  - Current user default value setting
  - Auto-fill current user in FormView member fields
- **⭐ Dashboard Templates** - Support saving dashboards as templates and reusing them
- **⭐ Enhanced Attachment Features** - Implemented backend file upload and frontend proxy access
  - MinIO object storage support
  - Image thumbnail generation
  - File type validation and security checks

##### 🔧 Bug Fixes

- **RecordDetailDrawer** - Auto-close drawer after saving record, improved UX
- **RecordHistoryDrawer** - Fixed drawer close behavior issue
- **Table View** - Fixed duplicate record creation issue, force refresh record list after creation
- **AppHeader** - Enhanced table and dashboard status display logic
- **Import/Export** - Optimized field type processing logic, improved compatibility
- **Excel Import** - Optimized import progress display and state management

##### 🎨 UI Improvements

- **Component Refactoring** - Moved collaboration components from Base page to AppHeader, global online status display
- **Base Page** - Moved statistics from top to bottom with style optimization
- **Table View** - Add record button and optimized action button group layout
- **Sidebar Buttons** - Added tooltip text to all buttons for enhanced usability
- **Field Icons** - Using Element Plus icon components for unified visual style

##### 🔒 Security Enhancements

- **XSS Protection** - Integrated DOMPurify for HTML content sanitization
- **Security Headers** - Added security-related HTTP response header middleware
- **API Rate Limiting** - Implemented IP-based API request rate limiting
- **File Upload Security** - Enhanced file upload security validation (MIME type, extension, size limits)
- **Password Reset** - Fixed verification bypass vulnerability in password reset route
- **Log Security** - Implemented sensitive information masking in production
- **Exception Handling** - Standardized exception information return to prevent information leakage

##### 📧 Email System

- **SMTP Integration** - Complete SMTP email sending functionality
- **Email Templates** - Customizable email template system
- **Email Queue** - Async email sending queue with retry mechanism
- **Email Logs** - Complete sending log recording and statistical analysis
- **Admin Panel** - Email configuration management, template editing, log viewing interface

##### 🔄 Real-time Collaboration Improvements

- **WebSocket Enhancement** - Improved connection stability and error handling
- **Debug Logging** - Added detailed debug logging for troubleshooting
- **User Names** - Collaboration supports displaying user name field
- **Authentication Enhancement** - Strengthened WebSocket connection authentication

### v1.1.0 - Released Version

#### Implemented Core Features ✅

##### Data Management

- [x] Base CRUD (Create, Edit, Delete, Star, Icon, Color)
- [x] Table CRUD (Create, Edit, Delete, Duplicate, Drag-sort, Star)
- [x] Field Management (26 types with configuration, sorting, visibility, default values, validation)
- [x] Record Management (CRUD, batch operations, detail drawer, change history)
- [x] Member Management (Base-level member list, add members, role assignment)
- [x] Sharing Management (Base sharing, form sharing, dashboard sharing)

##### View System

- [x] 6 View Types (Table, Kanban, Calendar, Gantt, Form, Gallery)
- [x] View Switching & Configuration Persistence
- [x] View-level Field Control (Hidden, Freeze, Width Adjustment)
- [x] Table View Advanced Features (Virtual Scroll, Column Freeze, Field Filter)
- [x] Form View Sharing (Public link, submission options, collector info collection)
- [x] Kanban View Drag-sort & Grouping

##### Data Processing

- [x] Data Filtering (Multi-condition, AND/OR logic, 20+ operators)
- [x] Data Sorting (Multi-field, ascending/descending, drag priority adjustment)
- [x] Data Grouping (Multi-level up to 3 levels, group statistics)
- [x] Formula Engine (43 built-in functions, field references, nested calculations, cross-table queries)
- [x] Data Import (Excel/CSV/JSON, multi-sheet, can create new tables)
- [x] Data Export (Excel/CSV/JSON, custom field selection)

##### User Experience

- [x] Drag Sorting (Tables, fields, views, Kanban cards)
- [x] Star Feature (Quick access to tables and dashboards)
- [x] Search Feature (Table names, record content full-text search)
- [x] Element Plus Icon System (Unified visual style)
- [x] Keyboard Shortcuts (Common operation shortcuts)
- [ ] Theme Switch (Light/Dark themes) 🚧 In Progress
- [ ] Responsive Design (Mobile adaptation) 🚧 In Progress

##### Permissions & Security

- [x] User Authentication (JWT Token, Refresh Token, Email Verification, Password Reset)
- [x] Role Permissions (Owner/Admin/Editor/Commenter/Viewer five-level permissions)
- [x] Sharing Permission Settings (Public/Private/Password protection, permission level control)
- [x] Security Protection (XSS protection, CSRF protection, rate limiting, security headers)
- [x] Operation Audit Logs (Complete user operation records)
- [ ] Field-level Permission Control 🚧 In Progress

##### Collaboration Features

- [x] Base-level Sharing (Link sharing, permission control)
- [x] Form View Public Sharing (Data collection, submission options)
- [x] Dashboard Public Sharing (Real-time data display, embed support)
- [x] Sharing Menu (My Shares / Shared with Me)
- [x] Real-time Collaboration (WebSocket, online presence, cell locking, conflict resolution, offline queue)
- [x] Operation History (Record-level change tracking)
- [ ] Comment & Annotation Features 🚧 In Progress

##### Dashboard System

- [x] Dashboard Basic Features (Create, Edit, Delete, Duplicate)
- [x] Multiple Chart Components (Number cards, clock, date, KPI, marquee, real-time charts, etc.)
- [x] Dashboard Templates (Save as template, create from template, template management)
- [x] Grid Layout (Flexible row/column config, component drag adjustment)
- [x] Real-time Data Updates (Dynamic data sources, scheduled refresh)
- [x] Dashboard Sharing (Public links, embed code)

##### Email System (Optional)

- [x] SMTP Configuration (Custom mail server)
- [x] Email Templates (Registration verification, password reset, etc.)
- [x] Email Queue (Async sending, failure retry)
- [x] Email Logs (Sending records, statistical analysis)
- [x] Admin Panel (Configuration management, template editing, log viewing)

### 🚧 Planned Features (Roadmap)

#### Near-term Plan (v1.3.0)

- [ ] **AI Feature Integration**
  - [ ] AI Form Builder (Natural language description to auto-generate business tables)
  - [ ] AI Form Assistant (Smart suggestions and data completion)
  - [ ] AI Data Q\&A (Natural language query for data analysis)
  - [ ] AI Data Visualization (Intelligent chart type recommendation)
- [ ] **Workflow Automation**
  - [ ] Workflow Designer (Visual business process design)
  - [ ] Automation Workflows (Triggers + Actions + Conditions)
  - [ ] Scheduled Tasks (Timed execution of automation workflows)
- [ ] **Plugin System**
  - [ ] Plugin Marketplace (Third-party plugin distribution)
  - [ ] Plugin SDK (Plugin development toolkit)
  - [ ] Script Extension (JavaScript/Python script execution)

#### Mid-term Plan (v2.0.0)

- [ ] **Open Platform**
  - [ ] REST API Improvement (More granular API control)
  - [ ] MCP Interface (Model Context Protocol integration)
  - [ ] Webhook (Event-triggered callbacks)
  - [ ] OAuth 2.0 Third-party Authorization
- [ ] **Documentation Features**
  - [ ] Document CRUD (Wiki-style document management)
  - [ ] Rich Text Editor Enhancement (Collaborative editing, version comparison)
  - [ ] Document Sharing & Version Management
  - [ ] Document-Table Integration
- [ ] **Mobile Adaptation**
  - [ ] Responsive Design Optimization
  - [ ] Mobile Native Apps (iOS/Android)
  - [ ] Enhanced Offline Mode (PWA support)

#### Long-term Vision

- [ ] **Enterprise Features**
  - [ ] SSO Single Sign-On (LDAP/OAuth/SAML)
  - [ ] Data Backup & Recovery
  - [ ] Multi-tenant Isolation
  - [ ] Compliance Reports (GDPR, etc.)
  - [ ] Enhanced Audit Logs (Operation replay)
- [ ] **Ecosystem Building**
  - [ ] Template Marketplace (Industry solution templates)
  - [ ] Integration Marketplace (Third-party service integrations)
  - [ ] Developer Community (API docs, SDK, examples)
  - [ ] Internationalization (i18n multi-language support)

## 📚 Detailed Documentation

- [Smart Table User Manual](./doc/Smart-Table-User-Manual.md) - Complete user operation guide
- [Technical Architecture Design](./doc/技术架构设计.md) - System architecture and technology selection
- [Product Planning Document](./doc/产品规划文档.md) - Product roadmap and feature planning
- [Development Task List](./doc/开发任务清单.md) - Development progress tracking
- [API Documentation](./doc/doc-b/API文档.md) - Backend API detailed documentation
- [Admin Guide](./doc/doc-b/ADMIN_GUIDE.md) - System administration manual
- [Deployment Guide](./doc/doc-b/部署指南.md) - Deployment and operations guide
- [Docker Deployment Docs](./doc/docker/DOCKER_DEPLOYMENT.md) - Docker deployment details
- [Security Audit Report](./doc/doc-f/Code-Quality-Security-Audit-Report.md) - Code security and quality audit
- [Release Notes](./RELEASE_NOTES.md) - Version update log

## 🤝 Contributing

Welcome to submit Issues and Pull Requests!

### Development Workflow

1. Fork this repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Develop and test
4. Commit your changes (`git commit -m 'feat: Add some AmazingFeature'`)
5. Push to the branch (`git push origin feature/AmazingFeature`)
6. Create a Pull Request with detailed description

### Commit Message Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/) specification:

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation update
- `style`: Code format changes (no functional impact)
- `refactor`: Code refactoring (neither new feature nor fix)
- `perf`: Performance optimization
- `test`: Test related
- `chore`: Build/tool/auxiliary tool changes

### Code Standards

- Frontend follows ESLint + Prettier configuration
- Backend follows PEP 8 standards
- Ensure all tests pass before committing: `npm run test` (frontend) / `pytest` (backend)
- Ensure TypeScript type checking passes: `vue-tsc --noEmit`

## 📄 License

This project is licensed under the [MIT License](LICENSE).

```
MIT License

Copyright (c) 2026 Smart Table Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

***

## 🙏 Acknowledgments

Thanks to all developers and users who contributed to this project!

Special thanks to:

- Vue.js team for the excellent frontend framework
- Element Plus team for the comprehensive UI component library
- Flask community for the flexible backend framework
- All Issue submitters and PR contributors

***

## 📞 Contact Us

- 📧 Email: <ldengbin@126.com>
- 💬 Issues: [GitHub Issues](https://github.com/ldbinac/smart_table/issues)
- 📖 Documentation: [User-Manual](https://github.com/ldbinac/smart_table/blob/main/doc/Smart-Table-User-Manual.md)

***

**⭐ If this project helps you, please give us a Star! ⭐**

**Made with ❤️ by Smart Table Team**
