const defaultApiBaseUrl = 'http://127.0.0.1:8000';

export const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? defaultApiBaseUrl;
export const API_BASE_URL = apiBaseUrl;
