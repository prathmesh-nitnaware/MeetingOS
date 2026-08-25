import React from "react"
import { render, screen, waitFor } from "@testing-library/react"
import { App } from "./App"
import { api } from "./services/api"
import { vi, describe, it, expect, beforeEach } from "vitest"

vi.mock("./services/api", () => {
  return {
    api: {
      getDashboardMetrics: vi.fn(),
      getMeetings: vi.fn(),
    },
  };
});

describe("MeetingOS Frontend App", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("renders layout shell and sidebar navigation links", async () => {
    // Setup resolving promises to prevent hung loading states
    (api.getDashboardMetrics as any).mockReturnValue(
      new Promise((resolve) =>
        resolve({
          meetings_ingested: 5,
          decisions_tracked: 12,
          open_actions: 4,
          overdue_actions: 1,
          unresolved_issues: 3,
          recurring_issues: 1,
          canonical_entities_tracked: 10,
          relationships_tracked: 8,
        })
      )
    );
    (api.getMeetings as any).mockReturnValue(new Promise((resolve) => resolve([])));

    render(<App />);

    expect(screen.getByText("MeetingOS")).toBeInTheDocument();
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Meetings")).toBeInTheDocument();
    expect(screen.getByText("Search & QA")).toBeInTheDocument();
    expect(screen.getByText("Entities & Graph")).toBeInTheDocument();
    expect(screen.getByText("Timeline Intelligence")).toBeInTheDocument();
  });

  it("renders loading spinner state when fetching dashboard metrics", async () => {
    // Delay resolve to capture loading spinner state
    (api.getDashboardMetrics as any).mockReturnValue(
      new Promise(() => {}) // Never resolves
    );
    (api.getMeetings as any).mockReturnValue(new Promise(() => {}));

    render(<App />);
    expect(screen.getByTestId("loading-spinner")).toBeInTheDocument();
  });

  it("renders dashboard metrics when api returns successfully", async () => {
    (api.getDashboardMetrics as any).mockResolvedValue({
      meetings_ingested: 8,
      decisions_tracked: 15,
      open_actions: 5,
      overdue_actions: 2,
      unresolved_issues: 4,
      recurring_issues: 2,
      canonical_entities_tracked: 12,
      relationships_tracked: 10,
    });
    (api.getMeetings as any).mockResolvedValue([]);

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText("Meetings Ingested")).toBeInTheDocument();
      expect(screen.getByText("Decisions Tracked")).toBeInTheDocument();
    });

    expect(screen.getByText("8")).toBeInTheDocument();
    expect(screen.getByText("15")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getAllByText("2").length).toBe(2);
    expect(screen.getByText("4")).toBeInTheDocument();
  });
});
