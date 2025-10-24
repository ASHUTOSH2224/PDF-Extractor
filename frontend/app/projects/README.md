# Projects Module - Architecture Documentation

## Overview

This module contains all project-related functionality including document extraction, annotation, and management. The code has been refactored into a clean, maintainable architecture following React best practices.

## Folder Structure

```
projects/
├── components/              # Reusable UI components
│   ├── extractors/         # Extractor page components
│   │   ├── PDFViewer.tsx           # PDF rendering component
│   │   ├── PageNavigation.tsx      # Page navigation controls
│   │   ├── RatingControl.tsx       # Star rating component
│   │   ├── ExtractorSelector.tsx   # Extractor dropdown selector
│   │   ├── ContentViewSelector.tsx # Content view mode toggle
│   │   ├── AnnotationPanel.tsx     # Annotation display & editing
│   │   ├── ExtractionJobsTable.tsx # Jobs summary table with sorting
│   │   └── index.ts
│   ├── documents/          # Document management components
│   │   ├── DocumentsTable.tsx      # Documents list table
│   │   └── index.ts
│   ├── project-card/       # Project card components
│   │   ├── ProjectCard.tsx         # Individual project card
│   │   └── index.ts
│   ├── new-project/        # New project form components
│   │   ├── ExtractionKeyForm.tsx   # Form for adding extraction keys
│   │   ├── ExtractionKeyList.tsx   # List of added extraction keys
│   │   └── index.ts
│   └── index.ts
├── hooks/                   # Custom React hooks
│   ├── usePDFViewer.ts            # PDF loading & rendering logic
│   ├── usePageContent.ts          # Page content fetching & management
│   ├── useExtractionJobPolling.ts # Job status polling & retry logic
│   └── index.ts
├── utils/                   # Utility functions
│   ├── formatters.ts              # Date, cost, latency formatters
│   ├── status-helpers.ts          # Status badge & retry helpers
│   ├── content-helpers.ts         # Content parsing & extraction
│   └── index.ts
├── types/                   # TypeScript type definitions
│   └── index.ts
├── [projectId]/            # Dynamic route folders
│   ├── documents/
│   │   └── [documentId]/
│   │       └── extractors/
│   │           └── page.tsx       # Main extractor page 
│   └── page.tsx                   # Project detail page
├── new/
│   └── page.tsx                   # New/Edit project page
└── README.md                      # This file
```

## Component Breakdown

### Extractor Components

#### PDFViewer
Handles PDF rendering using PDF.js.
- Props: `canvasRef`, `pdfError`, `loading`
- Displays loading state or error messages

#### PageNavigation
Provides intuitive page navigation with:
- Previous/Next buttons
- Page number buttons (shows 5 at a time)
- Jump to page input
- Ellipsis for large documents

#### RatingControl
Star rating component for user feedback:
- 5-star rating system
- Shows current rating
- Loading state during submission
- Error message display

#### ExtractorSelector
Dropdown to select between different extractors:
- Filtered to show only available extractors
- Updates content when changed

#### ContentViewSelector
Toggle between different content views:
- Combined, Text, Table modes
- Only shows available modes
- Smooth transitions

#### AnnotationPanel
Main annotation interface:
- Displays extracted content
- Allows text selection and annotation
- Create/delete annotations
- Integrates with AnnotatableText component

#### ExtractionJobsTable
Displays all extraction jobs with:
- Sortable columns (extractor, status, latency, cost, etc.)
- Status badges with color coding
- View and retry actions
- Loading states for retrying jobs

### Document Components

#### DocumentsTable
Lists all documents in a project:
- File name with icon
- Page count
- Upload date (relative format)
- View and delete actions
- Empty state

### Project Components

#### ProjectCard
Individual project card display:
- Project icon (PDF/Image)
- Name and description
- Owner information
- Creation date
- Delete button (owner only)

### New Project Components

#### ExtractionKeyForm
Form for adding extraction keys:
- Type selector (Key:Value, Value, Image)
- Field name and type inputs
- Description or image upload
- Validation

#### ExtractionKeyList
Displays added extraction keys:
- Badge for key type
- Field details
- Remove button

## Custom Hooks

### usePDFViewer
Manages PDF loading and rendering:
- Loads PDF.js library dynamically
- Fetches PDF with authentication
- Renders pages to canvas
- Handles errors gracefully

**Usage:**
```typescript
const { canvasRef, pdfError, currentPage, setCurrentPage } = usePDFViewer(pdfUrl, token, activeTab);
```

### usePageContent
Manages page content fetching:
- Loads extraction job pages
- Fetches annotations
- Handles loading and error states

**Usage:**
```typescript
const { pageContent, loadingPageContent, pageContentError, annotations, setAnnotations, fetchPageContent } = usePageContent(projectId, documentId, token, extractionJobs);
```

### useExtractionJobPolling
Handles job status updates:
- Polls for job status changes
- Supports job retry
- Auto-stops when all jobs complete
- Manages retry loading state

**Usage:**
```typescript
const { retryingJobs, retryExtractionJob, fetchExtractionJobs } = useExtractionJobPolling(projectId, documentId, token, extractionJobs, setExtractionJobs);
```

## Utility Functions

### Formatters
- `formatDate(dateString)` - Relative time formatting
- `formatLatency(latencyMs)` - Milliseconds to seconds
- `formatCost(cost)` - Dollar formatting with 4 decimals
- `formatRating(rating)` - Rating display format

### Status Helpers
- `getStatusConfig(status)` - Returns status configuration object with variant and text
- `canRetryJob(status)` - Checks if job can be retried
- `getRetryTooltip(status)` - Returns appropriate tooltip text

### Content Helpers
- `formatContentForDisplay(content)` - Extracts text from various formats
- `getContentInfo(content)` - Analyzes content structure
- `getContentForViewMode(content, viewMode)` - Gets content for specific view

## Type Definitions

All shared types are defined in `types/index.ts`:
- `ContentViewMode` - 'combined' | 'text' | 'table'
- `SortDirection` - 'asc' | 'desc'
- `SortField` - keyof DocumentExtractionJob | null
- Component prop interfaces

## Benefits of This Structure

1. **Maintainability**: Small, focused components are easier to understand and modify
2. **Reusability**: Components can be reused across different pages
3. **Testability**: Isolated components and hooks are easier to test
4. **Type Safety**: Centralized types ensure consistency
5. **Performance**: Custom hooks optimize re-renders
6. **Separation of Concerns**: Logic, UI, and utilities are clearly separated

## Code Reduction

- **Extractor Page**: 1143 lines → ~430 lines (62% reduction)
- **Project Page**: Cleaner with extracted DocumentsTable component
- **Home Page**: Cleaner with extracted ProjectCard component
- **New Project Page**: Better organized with form components

## Route Structure

The project uses Next.js App Router with the following URL patterns:

- `/projects/[projectId]` - Project detail page showing documents
- `/projects/[projectId]/documents/[documentId]/extractors` - Document extraction and annotation page
- `/projects/new` - Create new project page

Where:
- `[projectId]` is the project UUID from the API
- `[documentId]` is the document UUID from the API

## Migration Notes

- All existing functionality preserved
- No breaking changes to UI or UX
- All imports properly updated
- TypeScript strict mode compatible
- Linter error-free
- Updated route structure from `[pipelineId]` to `[projectId]` for consistency

