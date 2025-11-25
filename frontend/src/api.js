/**
 * API client for the LLM-COUNSEL backend.
 */

const API_BASE = 'http://localhost:8001';

export const api = {
  /**
   * List all matters.
   */
  async listMatters() {
    const response = await fetch(`${API_BASE}/api/matters`);
    if (!response.ok) {
      throw new Error('Failed to list matters');
    }
    return response.json();
  },

  /**
   * Create a new matter.
   */
  async createMatter(data = {}) {
    const response = await fetch(`${API_BASE}/api/matters`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        matter_name: data.matter_name || 'New Matter',
        practice_area: data.practice_area || 'civil',
        jurisdiction: data.jurisdiction || 'federal',
      }),
    });
    if (!response.ok) {
      throw new Error('Failed to create matter');
    }
    return response.json();
  },

  /**
   * Get a specific matter.
   */
  async getMatter(matterId) {
    const response = await fetch(`${API_BASE}/api/matters/${matterId}`);
    if (!response.ok) {
      throw new Error('Failed to get matter');
    }
    return response.json();
  },

  /**
   * Delete a matter.
   */
  async deleteMatter(matterId) {
    const response = await fetch(`${API_BASE}/api/matters/${matterId}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new Error('Failed to delete matter');
    }
    return response.json();
  },

  /**
   * Send a legal question in a matter.
   */
  async sendMessage(matterId, content, context = null) {
    const response = await fetch(
      `${API_BASE}/api/matters/${matterId}/message`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content, context }),
      }
    );
    if (!response.ok) {
      throw new Error('Failed to send message');
    }
    return response.json();
  },
};
