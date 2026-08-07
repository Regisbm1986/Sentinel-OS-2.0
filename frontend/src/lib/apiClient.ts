const API_BASE_URL = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");

const isAbsoluteUrl = (url: string): boolean => /^https?:\/\//i.test(url);

const resolvePath = (path: string): string => {
  if (!path) {
    return API_BASE_URL;
  }
  if (isAbsoluteUrl(path)) {
    return path;
  }
  const normalized = path.startsWith("/") ? path : `/${path}`;
  if (!API_BASE_URL) {
    return normalized;
  }
  return `${API_BASE_URL}${normalized}`;
};

export const apiFetch = (path: string, init?: RequestInit): Promise<Response> => {
  return fetch(resolvePath(path), init);
};

export const buildApiUrl = (path: string): string => {
  return resolvePath(path);
};
