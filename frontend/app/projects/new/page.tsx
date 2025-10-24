'use client'

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/card";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Textarea } from "../../components/ui/textarea";
import { Button } from "../../components/ui/button";
import Layout from "../../components/Layout";
import { useToast } from "../../hooks/useToast";
import { ExtractionKeyForm, ExtractionKeyList } from "../components/new-project";

type ExtractionKeyType = "key-value" | "value" | "image";

interface ExtractionKey {
  id: string;
  type: ExtractionKeyType;
  keyName: string;
  dataType: string;
  description?: string;
  imageFile?: File;
  location?: string;
}

// Mock project data for editing
const mockProjectData = {
  "1": {
    name: "Invoice Processing",
    description: "Extract data from invoice documents",
    keys: [
      {
        id: "1",
        type: "key-value" as ExtractionKeyType,
        keyName: "Invoice Number",
        dataType: "string",
        description: "Unique invoice identifier"
      },
      {
        id: "2", 
        type: "key-value" as ExtractionKeyType,
        keyName: "Total Amount",
        dataType: "number",
        description: "Total amount due"
      },
      {
        id: "3",
        type: "key-value" as ExtractionKeyType,
        keyName: "Vendor Name",
        dataType: "string",
        description: "Name of the vendor/company"
      }
    ]
  }
};

export default function NewProjectPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { toast } = useToast();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [keys, setKeys] = useState<ExtractionKey[]>([]);
  const [isEditMode, setIsEditMode] = useState(false);
  const [projectId, setProjectId] = useState<string | null>(null);
  
  // Current key being created
  const [currentType, setCurrentType] = useState<ExtractionKeyType>("key-value");
  const [currentKeyName, setCurrentKeyName] = useState("");
  const [currentDataType, setCurrentDataType] = useState("");
  const [currentDescription, setCurrentDescription] = useState("");
  const [currentImageFile, setCurrentImageFile] = useState<File | null>(null);

  // Initialize edit mode if edit parameter is present
  useEffect(() => {
    if (!searchParams) return;
    
    const editParam = searchParams.get('edit');
    if (editParam) {
      setIsEditMode(true);
      setProjectId(editParam);
      
      // Load existing project data
      const projectData = mockProjectData[editParam as keyof typeof mockProjectData];
      if (projectData) {
        setName(projectData.name);
        setDescription(projectData.description);
        setKeys(projectData.keys);
      }
    }
  }, [searchParams]);

  const handleAddKey = () => {
    if (!currentKeyName.trim()) {
      toast({
        title: "Error",
        description: "Field name is required",
        variant: "destructive",
      });
      return;
    }

    if (!currentDataType) {
      toast({
        title: "Error",
        description: "Field type is required",
        variant: "destructive",
      });
      return;
    }

    if (currentType === "image" && !currentImageFile) {
      toast({
        title: "Error",
        description: "Please upload a reference image",
        variant: "destructive",
      });
      return;
    }

    if (currentType !== "image" && !currentDescription.trim()) {
      toast({
        title: "Error",
        description: "Field description is required",
        variant: "destructive",
      });
      return;
    }

    const newKey: ExtractionKey = {
      id: Date.now().toString(),
      type: currentType,
      keyName: currentKeyName.trim(),
      dataType: currentDataType,
      description: currentDescription.trim() || undefined,
      imageFile: currentImageFile || undefined,
    };

    setKeys([...keys, newKey]);
    
    // Reset form
    setCurrentKeyName("");
    setCurrentDataType("");
    setCurrentDescription("");
    setCurrentImageFile(null);
  };

  const handleRemoveKey = (keyId: string) => {
    setKeys(keys.filter((key) => key.id !== keyId));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!name.trim()) {
      toast({
        title: "Error",
        description: "Project name is required",
        variant: "destructive",
      });
      return;
    }

    if (keys.length === 0) {
      toast({
        title: "Error",
        description: "At least one extraction key is required",
        variant: "destructive",
      });
      return;
    }

    toast({
      title: "Success",
      description: isEditMode ? "Project updated successfully" : "Project created successfully",
    });
    
    router.push("/");
  };

  return (
    <Layout>
      <div className="container mx-auto px-6 py-8 max-w-3xl">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-foreground mb-2">
            {isEditMode ? "Edit Project" : "Create New Project"}
          </h1>
          <p className="text-muted-foreground">
            {isEditMode ? "Update your document extraction project configuration" : "Configure a new document extraction project"}
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Project Configuration</CardTitle>
            <CardDescription>
              Define the project name, description, and extraction keys
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="name">Project Name</Label>
                <Input
                  id="name"
                  placeholder="e.g., Invoice Processing"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  maxLength={20}
                  required
                />
                <p className="text-xs text-muted-foreground">
                  {name.length}/20 characters
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  placeholder="Describe what this pipeline does..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  maxLength={50}
                  rows={3}
                />
                <p className="text-xs text-muted-foreground">
                  {description.length}/50 characters
                </p>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <Label>Extraction Keys</Label>
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground">Apply to all fields</span>
                    <div className="w-6 h-6 rounded-full bg-muted flex items-center justify-center text-xs font-medium">
                      {keys.length}
                    </div>
                  </div>
                </div>
                
                <ExtractionKeyForm
                  currentType={currentType}
                  currentKeyName={currentKeyName}
                  currentDataType={currentDataType}
                  currentDescription={currentDescription}
                  currentImageFile={currentImageFile}
                  onTypeChange={setCurrentType}
                  onKeyNameChange={setCurrentKeyName}
                  onDataTypeChange={setCurrentDataType}
                  onDescriptionChange={setCurrentDescription}
                  onImageFileChange={setCurrentImageFile}
                  onAddKey={handleAddKey}
                />

                <ExtractionKeyList
                  keys={keys}
                  onRemoveKey={handleRemoveKey}
                />
              </div>

              <div className="flex gap-3 pt-4">
                <Button type="submit" className="flex-1">
                  {isEditMode ? "Update Project" : "Create Project"}
                </Button>
                <Button type="button" variant="outline" onClick={() => router.push("/")}>
                  Cancel
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}
