# Smart Table

[中文](README.md) | English

A smart multi-dimensional table system based on Vue 3 + TypeScript + Pinia + Dexie (IndexedDB), similar to Airtable or Lark Base.

## Features

### Core Features

- Base Management - Create, edit, delete, and star bases
- Table Management - Support multiple tables with drag-sort, rename, and delete
- Field Management - Support 20+ field types
- Record Management - CRUD operations and batch actions
- View Management - Multiple view types with filter, sort, and group

### Supported Field Types

- Basic: Text, Number, Date, Checkbox
- Select: Single Select, Multi Select
- Contact: Member, Phone, Email, URL
- Media: Attachment
- Computed: Formula, Link, Lookup
- System: Created By, Created Time, Updated By, Updated Time, Auto Number
- Others: Rating, Progress

### Supported View Types

- Table View - Classic table display
- Kanban View - Card-based display
- Calendar View - Time-based display
- Gantt View - Project timeline display
- Form View - Data collection form
- Gallery View - Image card display

### Advanced Features

- Data Filtering - Multi-condition combined filtering
- Data Sorting - Multi-field sorting
- Data Grouping - Group by field
- Data Export - Support Excel, CSV formats
- Drag Sorting - Drag to sort tables, fields, and views
- Star Feature - Quick access to frequently used tables
- Search Feature - Quick table search

## Tech Stack

| Category             | Technology              |
| -------------------- | ----------------------- |
| Frontend Framework   | Vue 3 (Composition API) |
| Language             | TypeScript              |
| State Management     | Pinia                   |
| Database             | Dexie (IndexedDB)       |
| UI Component Library | Element Plus            |
| Table Component      | vxe-table               |
| Drag Sorting         | sortablejs              |
| Charts               | echarts + vue-echarts   |
| Build Tool           | Vite                    |
| Testing              | Vitest                  |

## Quick Start

### Requirements

- Node.js >= 18
- npm >= 9

### Install Dependencies

```bash
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
│   │   ├── fields/          # Field type components
│   │   ├── filters/         # Filter components
│   │   ├── groups/          # Group components
│   │   ├── sorts/           # Sort components
│   │   └── views/           # View components
│   ├── db/                  # Database layer
│   │   ├── services/        # Data services
│   │   ├── schema.ts        # Dexie database schema
│   │   └── __tests__/       # Test files
│   ├── layouts/             # Layout components
│   ├── router/              # Vue Router config
│   ├── stores/              # Pinia state management
│   ├── types/               # TypeScript type definitions
│   ├── utils/               # Utility functions
│   │   ├── export/          # Export functionality
│   │   └── formula/         # Formula engine
│   └── views/               # Page views
├── package.json
├── vite.config.ts
├── tsconfig.json
└── README.md
```

## Data Models

### Base

- Base unit for multi-dimensional tables
- Support starring, custom icon and color

### Table

- Contains field definitions and record data
- Support drag sorting and starring

### Field

- Define column types and properties
- Support 20+ field types

### Record

- Data row
- Support CRUD and batch operations

### View

- Data display method
- Support filter, sort, and group configuration

## Browser Support

- Chrome >= 90
- Firefox >= 88
- Safari >= 14
- Edge >= 90

## Roadmap

- [x] Base CRUD
- [x] Table CRUD
- [x] Field Management
- [x] Record Management
- [x] Multiple View Support
- [x] Data Filter & Sort
- [x] Data Export
- [x] Drag Sorting
- [x] Star Feature
- [x] Search Feature
- [ ] Data Import
- [ ] Collaboration Features
- [ ] Permission Management
- [ ] Automation Workflows

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

[MIT](LICENSE) © 2026 Smart Table Contributors
