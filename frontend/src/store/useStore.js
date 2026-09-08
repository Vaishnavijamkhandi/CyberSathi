import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import axios from 'axios';

export const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Synchronously read initial auth from localStorage to prevent flash of unauthenticated state
const getInitialAuth = () => {
  const token = localStorage.getItem('cybersaathi_token');
  let user = null;
  try {
    const rawUser = localStorage.getItem('cybersaathi_user');
    if (rawUser) user = JSON.parse(rawUser);
  } catch (e) {}
  return {
    token: token || null,
    user: user || null,
    isAuthenticated: Boolean(token),
  };
};

const initialAuth = getInitialAuth();

// Configure axios
const api = axios.create({ baseURL: API_BASE });
api.interceptors.request.use((config) => {
  let token = useStore.getState().token;
  if (!token) {
    token = localStorage.getItem('cybersaathi_token');
  }
  if (!token) {
    try {
      const persisted = JSON.parse(localStorage.getItem('cybersaathi-store') || '{}');
      token = persisted?.state?.token;
    } catch (e) {}
  }
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('cybersaathi_token');
      localStorage.removeItem('cybersaathi_user');
      localStorage.removeItem('cybersaathi-store');
      useStore.setState({ user: null, token: null, isAuthenticated: false });
      const currentPath = window.location.pathname;
      if (
        !currentPath.startsWith('/login') &&
        !currentPath.startsWith('/register') &&
        !currentPath.startsWith('/auth') &&
        currentPath !== '/'
      ) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export { api };

const useStore = create(
  persist(
    (set, get) => ({
      // ─── Auth ───────────────────────────────────────────────────────
      user: initialAuth.user,
      token: initialAuth.token,
      isAuthenticated: initialAuth.isAuthenticated,

      login: async (emailOrObj, passwordArg) => {
        let email, password;
        if (typeof emailOrObj === 'object' && emailOrObj !== null) {
          email = emailOrObj.email;
          password = emailOrObj.password;
        } else {
          email = emailOrObj;
          password = passwordArg;
        }
        const res = await api.post('/api/auth/login', { email, password });
        localStorage.setItem('cybersaathi_token', res.data.access_token);
        localStorage.setItem('cybersaathi_user', JSON.stringify(res.data.user));
        set({ token: res.data.access_token, user: res.data.user, isAuthenticated: true });
        return { ok: true, ...res.data };
      },

      register: async (emailOrObj, fullNameArg, passwordArg, phoneArg) => {
        let email, full_name, password, phone;
        if (typeof emailOrObj === 'object' && emailOrObj !== null) {
          email = emailOrObj.email;
          full_name = emailOrObj.full_name;
          password = emailOrObj.password;
          phone = emailOrObj.phone || '';
        } else {
          email = emailOrObj;
          full_name = fullNameArg;
          password = passwordArg;
          phone = phoneArg || '';
        }
        const res = await api.post('/api/auth/register', { email, full_name, password, phone });
        localStorage.setItem('cybersaathi_token', res.data.access_token);
        localStorage.setItem('cybersaathi_user', JSON.stringify(res.data.user));
        set({ token: res.data.access_token, user: res.data.user, isAuthenticated: true });
        return { ok: true, ...res.data };
      },

      logout: () => {
        localStorage.removeItem('cybersaathi_token');
        localStorage.removeItem('cybersaathi_user');
        set({ user: null, token: null, isAuthenticated: false, complaints: [] });
      },

      // ─── Active Complaint ────────────────────────────────────────────
      activeComplaintId: null,
      chatMessages: [],
      extractedEntities: {},
      classification: null,
      risk: null,
      missingInfo: [],
      evidenceChecklist: [],
      evidenceFiles: [],
      complaintText: '',
      incidentDescription: '',
      timeline: [],

      setActiveComplaint: (id) => set({ activeComplaintId: id }),

      startComplaint: async () => {
        const res = await api.post('/api/chat/start');
        set({
          activeComplaintId: res.data.complaint_id,
          chatMessages: [{
            role: 'assistant',
            content: "Namaste! I'm CyberSaathi, your AI cybercrime complaint assistant. I'm here to help you document and report a cybercrime incident. Please tell me what happened — describe the incident in your own words.",
            id: Date.now(),
          }],
          extractedEntities: {},
          classification: null,
          risk: null,
          missingInfo: [],
          evidenceChecklist: [],
          evidenceFiles: [],
          complaintText: '',
          incidentDescription: '',
          timeline: [],
        });
        return res.data.complaint_id;
      },

      sendMessage: async (message) => {
        const state = get();
        // Add user message immediately
        set((s) => ({
          chatMessages: [...s.chatMessages, { role: 'user', content: message, id: Date.now() }],
        }));

        const res = await api.post('/api/chat/message', {
          complaint_id: state.activeComplaintId,
          message,
        });

        // Add bot reply and update draft in real time
        set((s) => {
          const complaintId = res.data.complaint_id;
          const updatedComplaints = (s.complaints || []).map((c) => {
            if (String(c.id) === String(complaintId)) {
              return {
                ...c,
                title: res.data.title || c.title,
                crime_category: res.data.classification?.category || c.crime_category,
                risk_level: res.data.risk?.level || c.risk_level,
                risk_score: res.data.risk?.score || c.risk_score,
                complaint_text: res.data.complaint_text || c.complaint_text,
                incident_description: res.data.incident_description || c.incident_description,
                timeline: res.data.timeline || c.timeline,
                extracted_entities: res.data.extracted_entities || c.extracted_entities,
              };
            }
            return c;
          });

          return {
            chatMessages: [...s.chatMessages, { role: 'assistant', content: res.data.reply, id: Date.now() + 1 }],
            extractedEntities: res.data.extracted_entities || {},
            classification: res.data.classification || null,
            risk: res.data.risk || null,
            missingInfo: res.data.missing_info || [],
            evidenceChecklist: res.data.evidence_checklist || [],
            activeComplaintId: complaintId,
            complaintText: res.data.complaint_text || s.complaintText,
            incidentDescription: res.data.incident_description || s.incidentDescription,
            timeline: res.data.timeline || s.timeline,
            complaints: updatedComplaints,
          };
        });

        return res.data;
      },

      loadChatHistory: async (complaintId) => {
        try {
          const [chatRes, compRes] = await Promise.all([
            api.get(`/api/chat/${complaintId}/history`),
            api.get(`/api/complaint/${complaintId}`).catch(() => null),
          ]);
          const update = { chatMessages: chatRes.data.messages, activeComplaintId: complaintId };
          if (compRes?.data) {
            update.complaintText = compRes.data.complaint_text || update.complaintText;
            update.incidentDescription = compRes.data.incident_description;
            update.timeline = compRes.data.timeline || [];
            update.extractedEntities = compRes.data.extracted_entities || {};
            if (compRes.data.crime_category) {
              update.classification = {
                category: compRes.data.crime_category,
                confidence: compRes.data.crime_category_confidence,
              };
            }
            if (compRes.data.risk_level) {
              update.risk = {
                level: compRes.data.risk_level,
                score: compRes.data.risk_score,
              };
            }
          }
          set(update);
        } catch (e) {
          const res = await api.get(`/api/chat/${complaintId}/history`);
          set({ chatMessages: res.data.messages, activeComplaintId: complaintId });
        }
      },

      // ─── Evidence ────────────────────────────────────────────────────
      uploadEvidence: async (complaintIdOrFile, fileArg) => {
        const state = get();
        let complaintId = state.activeComplaintId;
        let file = complaintIdOrFile;
        if (fileArg !== undefined) {
          complaintId = complaintIdOrFile;
          file = fileArg;
        }
        const formData = new FormData();
        formData.append('complaint_id', complaintId);
        formData.append('file', file);
        const res = await api.post('/api/evidence/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
        const extractedText = res.data.extracted_text || res.data.ocr_text || '';
        const formatted = {
          id: res.data.id || res.data.evidence_id,
          filename: res.data.filename || file.name,
          file_type: res.data.file_type || 'image',
          document_type: res.data.document_type,
          extracted_text: extractedText,
          detected_entities: res.data.entities || res.data.detected_entities || {},
          ocr_preview: extractedText ? extractedText.slice(0, 200) : '',
        };
        set((s) => ({
          evidenceFiles: [...s.evidenceFiles, formatted],
          extractedEntities: { ...s.extractedEntities, ...(res.data.entities || res.data.merged_entities || {}) },
          complaintText: res.data.complaint_text || s.complaintText,
          timeline: res.data.timeline || s.timeline,
        }));
        return res.data;
      },

      loadEvidence: async (complaintId) => {
        const res = await api.get(`/api/evidence/${complaintId}`);
        const files = (res.data.evidence_files || []).map((f) => ({
          id: f.id,
          filename: f.filename,
          file_type: f.file_type,
          document_type: f.document_type,
          extracted_text: f.ocr_preview || f.extracted_text,
          detected_entities: f.entities || {},
          uploaded_at: f.uploaded_at,
        }));
        set({ evidenceFiles: files });
        return files;
      },

      deleteEvidence: async (evidenceId, complaintId) => {
        await api.delete(`/api/evidence/${evidenceId}`);
        set((s) => ({
          evidenceFiles: s.evidenceFiles.filter((f) => f.id !== evidenceId),
        }));
      },

      // ─── Complaint List ──────────────────────────────────────────────
      complaints: [],

      loadComplaints: async () => {
        const res = await api.get('/api/complaint/list');
        set({ complaints: res.data.complaints || [] });
      },

      generateComplaint: async () => {
        const state = get();
        const res = await api.post('/api/complaint/generate', {
          complaint_id: state.activeComplaintId,
        });
        return res.data;
      },

      // ─── ML Benchmark ────────────────────────────────────────────────
      benchmarkResults: null,
      benchmarkLoading: false,

      loadBenchmark: async () => {
        set({ benchmarkLoading: true });
        try {
          const res = await api.get('/api/ml/benchmark');
          set({ benchmarkResults: res.data, benchmarkLoading: false });
        } catch (e) {
          set({ benchmarkLoading: false });
        }
      },

      trainModels: async () => {
        await api.post('/api/ml/train');
      },
    }),
    {
      name: 'cybersaathi-store',
      partialize: (state) => ({ user: state.user, token: state.token, isAuthenticated: state.isAuthenticated }),
    }
  )
);

export default useStore;
