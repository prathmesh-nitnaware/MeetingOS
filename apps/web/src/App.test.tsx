import React from "react"
import { render, screen, waitFor, fireEvent } from "@testing-library/react"
import { App } from "./App"
import { api } from "./services/api"
import { vi, describe, it, expect, beforeEach } from "vitest"

vi.mock("./services/api", () => {
  return {
    api: {
      getDashboardMetrics: vi.fn(),
      listMeetings: vi.fn(),
      getMeetings: vi.fn(),
      listActionItems: vi.fn(),
      getActionItems: vi.fn(),
      listDecisions: vi.fn(),
      getDecisions: vi.fn(),
      getKnowledge: vi.fn(),
      getTeam: vi.fn(),
      search: vi.fn(),
      getActivityFeed: vi.fn(),
      getProjects: vi.fn(),
      getTopicDetail: vi.fn(),
    },
  }
})

describe("MeetingOS Text-First Frontend App", () => {
  beforeEach(() => {
    vi.resetAllMocks()
    localStorage.clear()

    ;(api.listMeetings as any).mockResolvedValue([
      {
        meeting_id: "m-1",
        title: "Q4 Product Launch Kickoff",
        meeting_date: "2026-09-29T10:00:00Z",
        source_type: "text",
        summary: "Discussed release schedule and architecture.",
        participant_count: 4,
        decisions_count: 2,
        actions_count: 3,
        topics: ["launch", "product"],
      },
    ])
    ;(api.listActionItems as any).mockResolvedValue([
      {
        id: "act-1",
        commitment_id: "act-1",
        task: "Complete authentication module",
        description: "Complete authentication module",
        owner_id: "Bob",
        status: "In Progress",
        due_date_str: "Oct 2",
      },
    ])
    ;(api.listDecisions as any).mockResolvedValue([
      {
        id: "dec-1",
        decision_id: "dec-1",
        title: "Internal release scheduled for Friday",
        subject: "Internal release scheduled for Friday",
        status: "agreed",
      },
    ])
    ;(api.getKnowledge as any).mockResolvedValue({
      topics: [{ name: "Product", count: 3 }],
      recurring_topics: [],
      recent_decisions: [],
      recent_actions: [],
      recent_key_points: [],
      total_meetings: 1,
    })
    ;(api.getTeam as any).mockResolvedValue([])
    ;(api.search as any).mockResolvedValue({ results: [], total: 0 })
    ;(api.getActivityFeed as any).mockResolvedValue([])
    ;(api.getProjects as any).mockResolvedValue([])
  })

  it("renders layout shell, header, and primary sidebar navigation links", async () => {
    render(<App />)

    expect(screen.getByText("MeetingOS")).toBeInTheDocument()
    expect(screen.getByText("Meeting Intelligence")).toBeInTheDocument()
    expect(screen.getByText("Dashboard")).toBeInTheDocument()
    expect(screen.getAllByText("Meetings").length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText("Action Items")).toBeInTheDocument()
    expect(screen.getByText("Decisions")).toBeInTheDocument()
    expect(screen.getByText("Knowledge & Topics")).toBeInTheDocument()
    expect(screen.getByText("Search & QA")).toBeInTheDocument()
    expect(screen.getByText("Team")).toBeInTheDocument()
    expect(screen.getByText("Settings")).toBeInTheDocument()
  })

  it("renders dashboard header greeting and search trigger", async () => {
    render(<App />)

    expect(screen.getByText(/Search meetings, decisions, actions/i)).toBeInTheDocument()
    expect(screen.getByText("New Meeting")).toBeInTheDocument()
  })

  it("opens global command palette modal on search trigger click", async () => {
    render(<App />)

    const searchTrigger = screen.getByText(/Search meetings, decisions, actions/i)
    fireEvent.click(searchTrigger)

    await waitFor(() => {
      expect(
        screen.getByPlaceholderText(/Search meetings, transcripts, decisions, action items, topics.../i)
      ).toBeInTheDocument()
    })
  })

  it("renders key metric counters and meeting intelligence on the dashboard", async () => {
    render(<App />)

    await waitFor(() => {
      expect(screen.getByText("Q4 Product Launch Kickoff")).toBeInTheDocument()
      expect(screen.getByText("Complete authentication module")).toBeInTheDocument()
      expect(screen.getByText("Internal release scheduled for Friday")).toBeInTheDocument()
    })
  })
})
