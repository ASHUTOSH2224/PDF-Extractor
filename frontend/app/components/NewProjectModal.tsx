'use client'

import { useState, useEffect } from 'react';
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Textarea } from "./ui/textarea";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";
import { useAuth } from "../contexts/AuthContext";

interface NewProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (projectData: ProjectData) => void;
  loading?: boolean;
}

interface ProjectData {
  name: string;
  file_upload_type: 'pdf' | 'image';
  description?: string;
}

export default function NewProjectModal({ isOpen, onClose, onSubmit, loading = false }: NewProjectModalProps) {
  const { user } = useAuth();
  const [formData, setFormData] = useState<ProjectData>({
    name: '',
    file_upload_type: 'pdf',
    description: '',
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (formData.name) {
      onSubmit(formData);
      setFormData({ name: '', file_upload_type: 'pdf', description: ''});
    }
  };

  const handleClose = () => {
    setFormData({ name: '', file_upload_type: 'pdf', description: ''});
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>
            Create New Project
          </DialogTitle>
          <DialogDescription>
            Create a new project to start extracting data from your documents.
          </DialogDescription>
        </DialogHeader>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Project Name</Label>
            <Input
              id="name"
              placeholder="Enter project name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              maxLength={20}
              required
            />
            <p className="text-xs text-muted-foreground">
              {formData.name.length}/20 characters
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="type">Document Type</Label>
            <div className="flex gap-2">
              <Button
                type="button"
                variant={formData.file_upload_type === 'pdf' ? 'default' : 'outline'}
                onClick={() => setFormData({ ...formData, file_upload_type: 'pdf' })}
                className="flex-1"
              >
                PDF
              </Button>
              <Button
                type="button"
                variant={formData.file_upload_type === 'image' ? 'default' : 'outline'}
                onClick={() => setFormData({ ...formData, file_upload_type: 'image' })}
                className="flex-1"
              >
                Image
              </Button>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              placeholder="Describe what this project will do (optional)"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              maxLength={50}
              rows={3}
            />
            <p className="text-xs text-muted-foreground">
              {(formData.description || '').length}/50 characters
            </p>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={handleClose} disabled={loading}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? 'Creating...' : 'Create Project'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
