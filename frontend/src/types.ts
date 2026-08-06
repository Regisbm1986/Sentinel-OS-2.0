export interface Job {
  id: string;
  title: string;
  company: string;
  location: string;
  salary: string;
  description: string;
  matchRate: number;
  atsVerdict: string; // "Excelente Match" | "Bom Match" | "Médio Match" | "Ajustes Necessários"
  applicationType: "auto" | "manual";
  link: string;
  requiredKeywords: string[];
  skillsGap: string[];
}

export interface OptimizationReport {
  score: number;
  keywords: string[];
  strengths: string[];
  missingSkills: string[];
  suggestions: string[];
  optimizedSummary: string;
  mockCoverLetter: string;
}

export interface LinkedInAnalysis {
  score: number;
  headline: string;
  aboutMe: string;
  recommendations: string[];
}

export interface Application {
  id: string;
  jobId: string;
  jobTitle: string;
  company: string;
  location: string;
  status: "scouted" | "applied" | "test" | "interview" | "offered" | "rejected";
  appliedAt: string;
  atsScore: number;
  coverLetterGenerated?: string;
  customSummaryUsed?: string;
  notes?: string;
}

export type PlanType = "free" | "pro" | "enterprise";

export interface LogEntry {
  id: string;
  timestamp: string;
  type: "info" | "success" | "warn" | "error";
  message: string;
}
