# Smart Table

[中文](README.md) | English

A smart multi-dimensional table system based on Vue 3 + TypeScript + Pinia + Dexie (IndexedDB), similar to Airtable or Lark Base.

## Features

### Core Features

- Base Management - Create, edit, delete, and star multi-dimensional tables
- Table Management - Support multiple tables with drag-sort, rename, and delete
- Field Management - Support 22 field types
- Record Management - CRUD operations and batch actions
- View Management - 6 view types with filter, sort, and group

### Supported Field Types (22 Types)

| Category | Field Type    | Status |
| -------- | ------------- | ------ |
| Basic    | Text          | ✅     |
| Basic    | Number        | ✅     |
| Basic    | Date          | ✅     |
| Basic    | Single Select | ✅     |
| Basic    | Multi Select  | ✅     |
| Basic    | Checkbox      | ✅     |
| Contact  | Member        | ✅     |
| Contact  | Phone         | ✅     |
| Contact  | Email         | ✅     |
| Contact  | URL           | ✅     |
| Media    | Attachment    | ✅     |
| Computed | Formula       | ✅     |
| Computed | Link          | ✅     |
| Computed | Lookup        | ✅     |
| System   | Created By    | ✅     |
| System   | Created Time  | ✅     |
| System   | Updated By    | ✅     |
| System   | Updated Time  | ✅     |
| System   | Auto Number   | ✅     |
| Others   | Rating        | ✅     |
| Others   | Progress      | ✅     |
| Others   | URL           | ✅     |

### Supported View Types (6 Types)

| View Type     | Description                                                 | Status |
| ------------- | ----------------------------------------------------------- | ------ |
| Table View    | Classic table display with virtual scroll and column freeze | ✅     |
| Kanban View   | Card-based display with drag sorting                        | ✅     |
| Calendar View | Time-based display                                          | ✅     |
| Gantt View    | Project timeline display                                    | ✅     |
| Form View     | Data collection form with sharing                           | ✅     |
| Gallery View  | Image card display                                          | ✅     |

### Advanced Features

- Data Filtering - Multi-condition combined filtering with AND/OR logic
- Data Sorting - Multi-field sorting
- Data Grouping - Group by field with statistics
- Data Import - Support Excel, CSV, JSON formats
- Data Export - Support Excel, CSV, JSON formats
- Formula Engine - 40+ built-in functions for math, text, date, logic, and statistics
- Drag Sorting - Drag to sort tables, fields, and views
- Star Feature - Quick access to frequently used tables
- Search Feature - Quick table search

## Feature Preview

| Feature     | Preview                               | Feature       | Preview                                   |
| ----------- | ------------------------------------- | ------------- | ----------------------------------------- |
| Home        | ![Home](./doc/home.jpeg)              | Home          | ![Home2](./doc/home-all.jpeg)             |
| Table View  | ![Table View](./doc/TableView.jpeg)   | Table View    | ![Table View](./doc/TableViewGroup.jpeg)  |
| Kanban View | ![Kanban View](./doc/KanbanView.jpeg) | Calendar View | ![Calendar View](./doc/CalendarView.jpeg) |
| Gantt View  | ![Gantt View](./doc/GanttView.jpeg)   | Form View     | ![Form View](./doc/FormView.jpeg)         |
| Form View   | ![Form View](./doc/FormView.jpeg)     | Dashboard     | ![Dashboard](./doc/Dashboard.jpeg)        |

## Tech Stack

| Category             | Technology            | Version  |
| -------------------- | --------------------- | -------- |
| Frontend Framework   | Vue 3                 | ^3.5.30  |
| Language             | TypeScript            | ~5.9.3   |
| State Management     | Pinia                 | ^2.3.1   |
| Database             | Dexie (IndexedDB)     | ^3.2.7   |
| UI Component Library | Element Plus          | ^2.13.6  |
| Table Component      | vxe-table             | ^4.18.7  |
| Drag Sorting         | sortablejs            | ^1.15.7  |
| Charts               | echarts + vue-echarts | ^5.6.0   |
| Date Processing      | dayjs                 | ^1.11.20 |
| Build Tool           | Vite                  | ^8.0.1   |
| Testing              | Vitest                | ^3.2.4   |

## Quick Start

### Requirements

- Node.js >= 18
- npm >= 9

### Install Dependencies

```bash
cd smart-table
npm install
```

### Development Mode

```bash
npm run dev
```

### Build for Production

```bash
npm run build
```

### Preview Production Build

```bash
npm run preview
```

### Run Tests

```bash
# Run all tests
npm run test

# Run tests in watch mode
npm run test:watch

# Generate test coverage report
npm run test:coverage
```

## Project Structure

```
smart-table/
├── src/
│   ├── assets/              # Static assets
│   │   └── styles/          # SCSS style files
│   ├── components/          # Vue components
│   │   ├── common/          # Common components
│   │   ├── dialogs/         # Dialog components
│   │   ├── fields/          # 22 field type components
│   │   ├── filters/         # Filter components
│   │   ├── groups/          # Group components
│   │   ├── sorts/           # Sort components
│   │   └── views/           # 6 view components
│   ├── db/                  # Database layer
│   │   ├── services/        # Data services (base/table/field/record/view/dashboard)
│   │   ├── schema.ts        # Dexie database schema
│   │   └── __tests__/       # Test files
│   ├── layouts/             # Layout components
│   ├── router/              # Vue Router config
│   ├── stores/              # Pinia state management
│   │   ├── baseStore.ts     # Base state
│   │   ├── tableStore.ts    # Table state
│   │   ├── viewStore.ts     # View state
│   │   └── ...
│   ├── types/               # TypeScript type definitions
│   │   ├── fields.ts        # Field type definitions
│   │   ├── views.ts         # View type definitions
│   │   └── filters.ts       # Filter type definitions
│   ├── utils/               # Utility functions
│   │   ├── export/          # Export functionality
│   │   ├── formula/         # Formula engine
│   │   ├── filter.ts        # Filter logic
│   │   ├── sort.ts          # Sort logic
│   │   └── group.ts         # Group logic
│   └── views/               # Page views
├── package.json
├── vite.config.ts
├── tsconfig.json
└── README.md
```

## Data Models

### Base (Multi-dimensional Table)

- Base unit for multi-dimensional tables
- Support starring, custom icon and color

### Table

- Contains field definitions and record data
- Support drag sorting and starring

### Field

- Define column types and properties
- Support 22 field types

### Record

- Data row
- Support CRUD and batch operations

### View

- Data display method
- Support filter, sort, and group configuration

## Formula Engine

Formula usage examples:

```
// Calculate total price
{Unit Price} * {Quantity}

// Calculate discounted price
{Original Price} * (1 - {Discount})

// Conditional judgment
IF({Score} >= 90, "Excellent", IF({Score} >= 60, "Pass", "Fail"))

// Text concatenation
CONCAT({First Name}, {Last Name})

// Date calculation
DATEDIF({Start Date}, {End Date}, "D")
```

Supports 40+ built-in functions:

### Math Functions

`SUM`, `AVG`, `MAX`, `MIN`, `ROUND`, `CEILING`, `FLOOR`, `ABS`, `MOD`, `POWER`, `SQRT`

### Text Functions

`CONCAT`, `LEFT`, `RIGHT`, `LEN`, `UPPER`, `LOWER`, `TRIM`, `SUBSTITUTE`, `REPLACE`, `FIND`

### Date Functions

`TODAY`, `NOW`, `YEAR`, `MONTH`, `DAY`, `HOUR`, `MINUTE`, `SECOND`, `DATEDIF`, `DATEADD`

### Logic Functions

`IF`, `AND`, `OR`, `NOT`, `IFERROR`, `IFS`, `SWITCH`

### Statistical Functions

`COUNT`, `COUNTA`, `COUNTIF`, `SUMIF`, `AVERAGEIF`

## Browser Support

- Chrome >= 90
- Firefox >= 88
- Safari >= 14
- Edge >= 90

## Development Roadmap

### Implemented Features ✅

- [x] Base CRUD
- [x] Table CRUD
- [x] Field Management (22 types)
- [x] Record Management
- [x] 6 View Support (Table, Kanban, Calendar, Gantt, Form, Gallery)
- [x] Data Filtering
- [x] Data Sorting
- [x] Data Grouping
- [x] Formula Engine (40+ functions)
- [x] Data Import (Excel/CSV/JSON)
- [x] Data Export (Excel/CSV/JSON)
- [x] Drag Sorting
- [x] Star Feature
- [x] Search Feature
- [x] Form View Sharing
- [x] Field Required Attribute
- [x] Field Validation Rules (Required, Number, Email, Phone, URL)
- [x] Attachment Field Upload/Download/Delete
- [x] Dashboard Basic Features

### Planned Features 📋

#### Field Enhancements
- [ ] Field Default Values
- [ ] Attachment Field Preview (Images, Documents, Videos, etc.)
- [ ] New Field Types (Text Area, ID Card, Geolocation)
- [ ] Formula Engine Documentation

#### View Enhancements
- [ ] Form View Enhancements (Linkage, Background Image, Description, Collector Info)
- [ ] Global Filter
- [ ] Field Linkage
- [ ] Dashboard Grid Configuration Optimization
- [ ] Template Features (Save Base/Dashboard as Template)
- [ ] Table View Column Freeze
- [ ] Table View Field Filter
- [ ] Group Mode Field Display Style Improvements

#### Sharing Features
- [ ] Base Sharing
- [ ] Single Table Sharing
- [ ] Single View Sharing
- [ ] Sharing Content Configuration
- [ ] Sharing Menu (My Shares / Shared with Me)

#### History & Collaboration
- [ ] Version History Management
- [ ] Change Log
- [ ] Collaboration Features (based on WebRTC)
- [ ] Permission Management

#### AI Features
- [ ] AI Form Builder (Build business tables with natural language)
- [ ] AI Form Assistant
- [ ] Data Q&A with Visualization

#### Workflow & Extensions
- [ ] Workflow Design
- [ ] Automation Workflows
- [ ] Script Extension Support
- [ ] Plugin System

#### Open APIs
- [ ] REST API Interface
- [ ] MCP Interface

#### Admin Console
- [ ] Admin Console (Java/Python Stack)

#### Documentation Features
- [ ] Document CRUD
- [ ] Rich Text Editor
- [ ] Document Sharing & Version Management

#### Others
- [ ] Mobile Adaptation
- [ ] User Manual Documentation

## Contributing

Welcome to submit Issues and Pull Requests!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Create a Pull Request

## License

[MIT](LICENSE) © 2026 Smart Table Contributors
