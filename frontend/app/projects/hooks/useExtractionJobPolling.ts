import { useState, useCallback, useEffect } from 'react';
import { apiService, DocumentExtractionJob } from '../../services/api';

export function useExtractionJobPolling(
  projectId: string,
  documentId: string,
  token: string | null,
  extractionJobs: DocumentExtractionJob[],
  setExtractionJobs: (jobs: DocumentExtractionJob[]) => void,
  filterByUser: boolean = false
) {
  const [retryingJobs, setRetryingJobs] = useState<Set<string>>(new Set());
  const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null);

  // Fetch extraction jobs
  const fetchExtractionJobs = useCallback(async () => {
    if (!projectId || !documentId || !token) {
      return;
    }

    try {
      const jobsData = await apiService.getDocumentExtractionJobs(projectId, documentId, token, filterByUser);
      setExtractionJobs(jobsData);
    } catch (error) {
      console.error('Failed to fetch extraction jobs:', error);
    }
  }, [projectId, documentId, token, filterByUser, setExtractionJobs]);

  // Start polling for status updates
  const startPolling = useCallback(() => {
    if (pollingInterval) {
      clearInterval(pollingInterval);
    }
    
    const interval = setInterval(async () => {
      try {
        await fetchExtractionJobs();
        
        // Check if all jobs are completed (not processing)
        const allCompleted = extractionJobs.every(job => 
          job.status !== 'Processing' && job.status !== 'NOT_STARTED'
        );
        
        if (allCompleted) {
          clearInterval(interval);
          setPollingInterval(null);
        }
      } catch (error) {
        console.error('Error polling extraction jobs:', error);
      }
    }, 3000); // Poll every 3 seconds
    
    setPollingInterval(interval);
  }, [pollingInterval, fetchExtractionJobs]);

  // Stop polling
  const stopPolling = useCallback(() => {
    if (pollingInterval) {
      clearInterval(pollingInterval);
      setPollingInterval(null);
    }
  }, [pollingInterval]);

  // Retry extraction job
  const retryExtractionJob = async (jobUuid: string) => {
    if (!projectId || !documentId || !token) {
      return;
    }

    try {
      setRetryingJobs(prev => new Set(prev).add(jobUuid));
      
      await apiService.retryExtractionJob(projectId, documentId, jobUuid, token);
      
      // Start polling for status updates
      startPolling();
      
      // Refresh extraction jobs
      await fetchExtractionJobs();
      
    } catch (error) {
      console.error('Failed to retry extraction job:', error);
    } finally {
      setRetryingJobs(prev => {
        const newSet = new Set(prev);
        newSet.delete(jobUuid);
        return newSet;
      });
    }
  };

  // Cleanup polling interval on unmount
  useEffect(() => {
    return () => {
      stopPolling();
    };
  }, [stopPolling]);

  // Auto-start polling if there are processing jobs
  useEffect(() => {
    const hasProcessingJobs = extractionJobs.some(job => 
      job.status === 'Processing' || job.status === 'NOT_STARTED'
    );
    
    if (hasProcessingJobs && !pollingInterval) {
      startPolling();
    } else if (!hasProcessingJobs && pollingInterval) {
      stopPolling();
    }
  }, [extractionJobs, pollingInterval, startPolling, stopPolling]);

  return {
    retryingJobs,
    retryExtractionJob,
    fetchExtractionJobs
  };
}

