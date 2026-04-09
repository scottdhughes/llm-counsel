/**
 * API client for the LLM-COUNSEL backend.
 * Uses Vite's dev proxy (see vite.config.js) to forward /api → backend.
 */

const API_BASE = '';  // empty → same origin → Vite proxy routes /api → :8001

async function jsonOrThrow(response, action) {
  if (!response.ok) {
    let detail = '';
    try {
      const body = await response.json();
      detail = body?.detail ? `: ${body.detail}` : '';
    } catch {
      // body wasn't JSON — fall through with status code only
    }
    throw new Error(`${action} failed (HTTP ${response.status})${detail}`);
  }
  return response.json();
}

export const api = {
  async listMatters() {
    const res = await fetch(`${API_BASE}/api/matters`);
    return jsonOrThrow(res, 'List matters');
  },

  async createMatter(data = {}) {
    const res = await fetch(`${API_BASE}/api/matters`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        matter_name: data.matter_name || 'New Matter',
        practice_area: data.practice_area || 'civil',
        jurisdiction: data.jurisdiction || 'federal',
      }),
    });
    return jsonOrThrow(res, 'Create matter');
  },

  async getMatter(matterId) {
    const res = await fetch(`${API_BASE}/api/matters/${matterId}`);
    return jsonOrThrow(res, 'Get matter');
  },

  async updateMatter(matterId, updates) {
    const res = await fetch(`${API_BASE}/api/matters/${matterId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    });
    return jsonOrThrow(res, 'Update matter');
  },

  async deleteMatter(matterId) {
    const res = await fetch(`${API_BASE}/api/matters/${matterId}`, {
      method: 'DELETE',
    });
    return jsonOrThrow(res, 'Delete matter');
  },

  async sendMessage(matterId, content, context = null) {
    const res = await fetch(`${API_BASE}/api/matters/${matterId}/message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, context }),
    });
    return jsonOrThrow(res, 'Send message');
  },

  async getTeamConfig() {
    const res = await fetch(`${API_BASE}/api/config/team`);
    return jsonOrThrow(res, 'Get team config');
  },
};
