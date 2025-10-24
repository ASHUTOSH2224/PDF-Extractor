# Projects Folder Structure Overview

## Visual Structure Tree

```
app/projects/
│
├── 📁 components/                          # All reusable components
│   │
│   ├── 📁 extractors/                      # Extractor page components (7 components)
│   │   ├── PDFViewer.tsx                   # 35 lines - PDF rendering
│   │   ├── PageNavigation.tsx              # 110 lines - Page controls
│   │   ├── RatingControl.tsx               # 40 lines - Star rating
│   │   ├── ExtractorSelector.tsx           # 30 lines - Dropdown selector
│   │   ├── ContentViewSelector.tsx         # 55 lines - View mode toggle
│   │   ├── AnnotationPanel.tsx             # 105 lines - Annotation interface
│   │   ├── ExtractionJobsTable.tsx         # 125 lines - Jobs table with sorting
│   │   └── index.ts                        # Exports
│   │
│   ├── 📁 documents/                       # Document components
│   │   ├── DocumentsTable.tsx              # 75 lines - Document list
│   │   └── index.ts
│   │
│   ├── 📁 project-card/                    # Project card component
│   │   ├── ProjectCard.tsx                 # 70 lines - Project card UI
│   │   └── index.ts
│   │
│   ├── 📁 new-project/                     # New project form components
│   │   ├── ExtractionKeyForm.tsx           # 120 lines - Key form
│   │   ├── ExtractionKeyList.tsx           # 60 lines - Keys list
│   │   └── index.ts
│   │
│   └── index.ts                            # Main exports
│
├── 📁 hooks/                               # Custom React hooks
│   ├── usePDFViewer.ts                     # 100 lines - PDF logic
│   ├── usePageContent.ts                   # 75 lines - Content fetching
│   ├── useExtractionJobPolling.ts          # 100 lines - Job polling
│   └── index.ts
│
├── 📁 utils/                               # Utility functions
│   ├── formatters.ts                       # 35 lines - Format helpers
│   ├── status-helpers.ts                   # 45 lines - Status utilities
│   ├── content-helpers.ts                  # 70 lines - Content parsing
│   └── index.ts
│
├── 📁 types/                               # TypeScript definitions
│   └── index.ts                            # 55 lines - All types
│
├── 📁 [projectId]/                         # Dynamic routes
│   ├── 📁 documents/
│   │   └── 📁 [documentId]/
│   │       └── 📁 extractors/
│   │           └── page.tsx                # 430 lines (was 1143 lines!)
│   └── page.tsx                            # 180 lines - Project details
│
├── 📁 new/
│   └── page.tsx                            # 220 lines - New/edit project
│
├── README.md                               # Full documentation
└── STRUCTURE_OVERVIEW.md                   # This file
```

## Component Hierarchy

### Extractor Page Flow
```
FileExtractorsPage (page.tsx)
├── Layout
├── Tabs (Summary/Annotation)
│   │
│   ├── Summary Tab
│   │   └── ExtractionJobsTable
│   │       ├── Status Badges
│   │       ├── Sortable Headers
│   │       └── Action Buttons
│   │
│   └── Annotation Tab
│       ├── Left Panel (PDF)
│       │   ├── PageNavigation
│       │   └── PDFViewer
│       │
│       └── Right Panel (Annotation)
│           ├── RatingControl
│           ├── ExtractorSelector
│           ├── ContentViewSelector
│           └── AnnotationPanel
│               └── AnnotatableText
```

### Project Detail Page Flow
```
ProjectDetailPage (page.tsx)
├── Layout
├── Project Header
│   ├── Back Button
│   ├── Project Info
│   └── Upload Button
│
├── Documents Card
│   └── DocumentsTable
│       └── Document Rows
│
├── UploadFileModal
└── ConfirmationDialog
```

### Home Page Flow
```
HomePage (app/page.tsx)
├── Layout
├── Header
│   └── New Project Button
│
├── Projects Grid
│   └── ProjectCard (multiple)
│       ├── Project Icon
│       ├── Project Info
│       └── Delete Button
│
├── NewProjectModal
└── ConfirmationDialog
```

### New Project Page Flow
```
NewProjectPage (projects/new/page.tsx)
├── Layout
├── Form Header
└── Project Form
    ├── Name Input
    ├── Description Input
    ├── ExtractionKeyForm
    ├── ExtractionKeyList
    └── Submit Buttons
```

## Hook Dependencies

```
usePDFViewer
├── Uses: pdfUrl, token, activeTab
└── Returns: canvasRef, pdfError, currentPage, setCurrentPage

usePageContent
├── Uses: projectId, documentId, token, extractionJobs
├── Calls: apiService.getExtractionJobPages
└── Returns: pageContent, loadingPageContent, pageContentError, annotations, fetchPageContent

useExtractionJobPolling
├── Uses: projectId, documentId, token, extractionJobs
├── Calls: apiService.retryExtractionJob
└── Returns: retryingJobs, retryExtractionJob, fetchExtractionJobs
```

## Utility Usage Map

```
formatters.ts
├── Used in: ExtractionJobsTable, DocumentsTable, ProjectCard
└── Functions: formatDate, formatLatency, formatCost, formatRating

status-helpers.ts
├── Used in: ExtractionJobsTable
└── Functions: getStatusConfig, canRetryJob, getRetryTooltip

content-helpers.ts
├── Used in: AnnotationPanel, FileExtractorsPage
└── Functions: formatContentForDisplay, getContentInfo, getContentForViewMode
```

## Route URLs

- **Project Detail**: `/projects/[projectId]` → `[projectId]/page.tsx`
- **Document Extractors**: `/projects/[projectId]/documents/[documentId]/extractors` → `[projectId]/documents/[documentId]/extractors/page.tsx`
- **New Project**: `/projects/new` → `new/page.tsx`

## Quick Navigation

- **Need to modify PDF viewer?** → `components/extractors/PDFViewer.tsx`
- **Need to change rating UI?** → `components/extractors/RatingControl.tsx`
- **Need to update job table?** → `components/extractors/ExtractionJobsTable.tsx`
- **Need to add new hook?** → `hooks/`
- **Need to add utility?** → `utils/`
- **Need to add types?** → `types/index.ts`
- **Need to modify project routes?** → `[projectId]/` folder
