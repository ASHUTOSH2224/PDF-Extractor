'use client'

import React from 'react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../../components/ui/select";
import { DocumentExtractionJob } from "../../../services/api";

interface ExtractorSelectorProps {
  selectedExtractor: string;
  extractionJobs: DocumentExtractionJob[];
  onSelectExtractor: (extractor: string) => void;
}

export function ExtractorSelector({ selectedExtractor, extractionJobs, onSelectExtractor }: ExtractorSelectorProps) {
  // Filter to only show successful extraction jobs
  const successfulJobs = extractionJobs.filter(job => job.status === 'Success');
  
  return (
    <Select value={selectedExtractor} onValueChange={onSelectExtractor}>
      <SelectTrigger className="w-48 h-8">
        <SelectValue placeholder="Select extractor" />
      </SelectTrigger>
      <SelectContent>
        {successfulJobs.map((job) => (
          <SelectItem key={job.uuid} value={job.extractor}>
            {job.extractor}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

