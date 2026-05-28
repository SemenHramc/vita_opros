import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  headers: {
    "X-API-Key": process.env.REACT_APP_API_KEY || "change-me-in-production",
  },
});

export const fetchWeeks = () => api.get("/weeks").then((r) => r.data);
export const fetchSummary = (weekStart) => api.get(`/summary/${weekStart}`).then((r) => r.data);
export const fetchResponses = (weekStart) => api.get(`/responses/${weekStart}`).then((r) => r.data);
export const fetchHeatmap = (weekStart, clientId) =>
  api.get(`/heatmap/${weekStart}`, { params: { client_id: clientId } }).then((r) => r.data);
export const fetchClientBlockers = (weekStart, clientId) =>
  api.get(`/client-blockers/${weekStart}`, { params: { client_id: clientId } }).then((r) => r.data);
export const fetchDynamics = (employeeId) =>
  api.get("/dynamics", { params: { employee_id: employeeId } }).then((r) => r.data);
export const fetchEmployees = () => api.get("/employees").then((r) => r.data);
export const fetchClients = () => api.get("/clients").then((r) => r.data);
export const fetchVacations = () => api.get("/vacations").then((r) => r.data);
export const saveVacations = (data) => api.post("/vacations", data).then((r) => r.data);

async function downloadFile(url, filename) {
  const response = await api.get(url, { responseType: "blob" });
  const blobUrl = window.URL.createObjectURL(response.data);
  const link = document.createElement("a");
  link.href = blobUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(blobUrl);
}

export const exportCsv = (weekStart) => downloadFile(`/export/${weekStart}/csv`, `survey_${weekStart}.csv`);
export const exportXlsx = (weekStart) =>
  downloadFile(
    `/export/${weekStart}/xlsx`,
    `survey_${weekStart}.xlsx`
  );

export function getApiErrorMessage(error, fallbackMessage) {
  return error?.response?.data?.detail || fallbackMessage;
}