# PDF Extraction Tool - Frontend

A modern, secure document extraction platform built with Next.js 14, featuring AI-powered PDF processing, user management, and real-time extraction monitoring.

## 🚀 Features

### Core Functionality
- **Document Processing**: Upload and process PDFs with multiple AI extraction engines
- **Project Management**: Organize documents into projects with detailed tracking
- **Real-time Monitoring**: Track extraction jobs, performance metrics, and processing status
- **Multi-Engine Support**: Choose from various extraction engines (PyPDF2, PyMuPDF, PDFPlumber, Camelot, Tesseract, Textract, Mathpix, Tabula, Unstructured, OpenAI GPT, MarkItDown, LlamaParse)

### User Management & Security
- **Admin Approval Workflow**: New users require admin approval before accessing the platform
- **Role-Based Access Control**: Admin and user roles with appropriate permissions
- **JWT Authentication**: Secure token-based authentication with role validation
- **User Management**: Admin panel for approving, activating, and managing users

### User Experience
- **Modern UI**: Built with shadcn/ui components and Tailwind CSS
- **Responsive Design**: Optimized for desktop and mobile devices
- **Interactive Document Viewer**: Side-by-side PDF viewing with extracted content
- **Annotation System**: Add comments and feedback to extracted content
- **Rating System**: Rate extraction quality for continuous improvement

## 🛠 Tech Stack

- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **UI Components**: shadcn/ui (Radix UI primitives)
- **Icons**: Lucide React
- **State Management**: TanStack Query (React Query)
- **Authentication**: JWT with role-based access control
- **Theme**: next-themes for dark/light mode support

## 📁 Project Structure

```
frontend/
├── app/                          # Next.js App Router
│   ├── admin/                    # Admin management pages
│   │   └── page.tsx             # User management interface
│   ├── components/              # Reusable components
│   │   ├── ui/                  # shadcn/ui components
│   │   ├── Layout.tsx           # Main application layout
│   │   ├── LoginForm.tsx        # Authentication forms
│   │   ├── ProtectedRoute.tsx   # Route protection wrapper
│   │   └── UploadFileModal.tsx  # File upload interface
│   ├── contexts/                # React contexts
│   │   └── AuthContext.tsx      # Authentication state management
│   ├── hooks/                   # Custom React hooks
│   ├── lib/                     # Utility functions
│   ├── projects/                # Project-related pages
│   │   ├── [projectId]/         # Project detail pages
│   │   │   ├── documents/       # Document management
│   │   │   └── page.tsx         # Project overview
│   │   ├── components/          # Project-specific components
│   │   ├── hooks/               # Project-related hooks
│   │   ├── new/                 # Create new project
│   │   └── types/               # TypeScript definitions
│   ├── services/                # API services
│   │   └── api.ts               # Backend API client
│   ├── globals.css              # Global styles
│   ├── layout.tsx               # Root layout
│   ├── page.tsx                 # Home page (Projects dashboard)
│   └── providers.tsx            # Client providers
├── public/                      # Static assets
├── components.json              # shadcn/ui configuration
├── tailwind.config.ts           # Tailwind CSS configuration
└── package.json                 # Dependencies and scripts
```

## 🚦 Getting Started

### Prerequisites

- Node.js 18+ 
- npm, yarn, or pnpm
- Backend API running (see backend documentation)

### Installation

1. **Clone the repository**:
```bash
git clone <repository-url>
cd pdf-extraction-tool/frontend
```

2. **Install dependencies**:
```bash
npm install
# or
yarn install
# or
pnpm install
```

3. **Configure environment variables**:
Create a `.env.local` file in the frontend directory:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

4. **Run the development server**:
```bash
npm run dev
# or
yarn dev
# or
pnpm dev
```

5. **Open your browser**:
Navigate to [http://localhost:3000](http://localhost:3000)

## 📱 Key Pages & Features

### Authentication
- **Login/Signup** (`/`): Secure authentication with admin approval workflow
- **Protected Routes**: All pages require authentication and appropriate permissions

### Project Management
- **Projects Dashboard** (`/`): Overview of all projects with creation and management
- **New Project** (`/projects/new`): Create new extraction projects with configuration
- **Project Detail** (`/projects/[id]`): View project performance, documents, and settings

### Document Processing
- **Document Upload**: Drag-and-drop file upload with multiple extraction engine selection
- **Document Viewer** (`/projects/[projectId]/documents/[documentId]/extractors`): 
  - Side-by-side PDF and extracted content viewing
  - Interactive annotation system
  - Quality rating and feedback
  - Multiple extraction engine results comparison

### Admin Panel
- **User Management** (`/admin`): 
  - Approve pending user registrations
  - Activate/deactivate user accounts
  - Reset user passwords
  - View user roles and status

## 🔧 Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint

## 🔐 Authentication Flow

1. **User Registration**: Users sign up and are placed in "pending" status
2. **Admin Approval**: Administrators approve users through the admin panel
3. **Login Access**: Only approved and active users can log in
4. **Role-Based Access**: Admin users have access to user management features

## 🎨 UI Components

Built with shadcn/ui components for consistency and accessibility:
- Form components (Input, Button, Select, etc.)
- Layout components (Card, Dialog, Sheet, etc.)
- Feedback components (Toast, Alert, etc.)
- Navigation components (Tabs, Dropdown, etc.)

## 🌐 API Integration

The frontend communicates with the backend through a comprehensive API client (`services/api.ts`) that handles:
- Authentication and user management
- Project and document operations
- Extraction job monitoring
- File uploads and downloads
- Admin operations

## 🚀 Deployment

### Production Build
```bash
npm run build
npm run start
```

### Environment Variables
Ensure the following environment variables are set:
- `NEXT_PUBLIC_API_URL`: Backend API URL

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** and test thoroughly
4. **Commit your changes**: `git commit -m 'Add amazing feature'`
5. **Push to the branch**: `git push origin feature/amazing-feature`
6. **Open a Pull Request**

### Development Guidelines

- Follow TypeScript best practices
- Use the existing component library (shadcn/ui)
- Write meaningful commit messages
- Test your changes thoroughly
- Ensure responsive design
- Follow the existing code style

## 📄 License

MIT License - see [LICENSE](../../LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check the backend documentation for API details
- **Issues**: Report bugs and feature requests via GitHub Issues
- **Discussions**: Join community discussions for questions and ideas

---

Built with ❤️ using Next.js, TypeScript, and modern web technologies.