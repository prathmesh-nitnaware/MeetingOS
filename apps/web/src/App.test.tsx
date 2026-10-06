import React from "react"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { App } from "./App"
import { Modal } from "./components/Modal"
import EntitiesList from "./pages/EntitiesList"
import { api, describeErrorBody } from "./services/api"
import { endOfDayIso, formatDate, formatDuration } from "./utils/format"

const METRICS = {
  meetings_ingested: 8,
  decisions_tracked: 15,
  open_actions: 5,
  overdue_actions: 2,
  unresolved_issues: 4,
  recurring_issues: 2,
  canonical_entities_tracked: 12,
  relationships_tracked: 10,
}

const PROFILE = {
  user_id: "admin-dev",
  email: "admin@meetingos.local",
  full_name: "Dev Admin",
  role: "admin",
  org_id: "org_dev",
  organization_name: "Development Workspace",
  organization_slug: "dev-workspace",
  permissions: ["meetings.read", "meetings.create", "meetings.delete"],
  organizations: [],
}

afterEach(() => {
  vi.restoreAllMocks()
  localStorage.clear()
})

describe("App shell and sign-in", () => {
  beforeEach(() => {
    vi.spyOn(api, "getAuthConfig").mockResolvedValue({ dev_auth_enabled: false, dev_personas: [] })
    vi.spyOn(api, "getHealth").mockResolvedValue({
      status: "healthy",
      app_name: "MeetingOS API",
      version: "1.0.0-rc1",
      environment: "test",
      dependencies: { database: true, redis: true },
    })
  })

  it("shows the sign-in page when there is no session (no silent admin fallback)", async () => {
    render(<App />)
    expect(await screen.findByRole("button", { name: "Sign in" })).toBeInTheDocument()
    expect(screen.getByLabelText("Password")).toBeInTheDocument()
  })

  it("renders the dashboard for a signed-in user", async () => {
    localStorage.setItem("meetingos_token", "token-123")
    vi.spyOn(api, "getProfile").mockResolvedValue(PROFILE)
    vi.spyOn(api, "getDashboardMetrics").mockResolvedValue(METRICS)
    vi.spyOn(api, "getMeetings").mockResolvedValue([])

    render(<App />)

    await waitFor(() => expect(screen.getByText("Meetings ingested")).toBeInTheDocument())
    expect(screen.getByText("15")).toBeInTheDocument()
    expect(screen.getByText("Dev Admin")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /sign out/i })).toBeInTheDocument()
  })
})

describe("API error formatting", () => {
  it("turns FastAPI validation lists into readable text instead of [object Object]", () => {
    const text = describeErrorBody(
      { detail: [{ loc: ["body", "title"], msg: "String should have at most 500 characters" }] },
      "fallback"
    )
    expect(text).toBe("Title: String should have at most 500 characters")
    expect(describeErrorBody({ detail: "Plain message" }, "fallback")).toBe("Plain message")
  })
})

describe("Entities page", () => {
  it("renders entities using the API field names without crashing", async () => {
    vi.spyOn(api, "listCanonicalEntities").mockResolvedValue([
      { id: "ent-postgresql", name: "PostgreSQL", entity_type: "TECHNOLOGY", meeting_count: 2, meetings: ["m1", "m2"] },
    ])
    render(
      <MemoryRouter>
        <EntitiesList />
      </MemoryRouter>
    )
    expect(await screen.findByText("PostgreSQL")).toBeInTheDocument()
    expect(screen.getByText("TECHNOLOGY")).toBeInTheDocument()
    expect(screen.getByText("Mentioned in 2 meetings")).toBeInTheDocument()
  })
})

describe("Modal", () => {
  it("closes on Escape and is announced as a dialog", () => {
    const onClose = vi.fn()
    render(
      <Modal isOpen onClose={onClose} title="Example">
        <input aria-label="field" />
      </Modal>
    )
    expect(screen.getByRole("dialog", { name: "Example" })).toBeInTheDocument()
    fireEvent.keyDown(document, { key: "Escape" })
    expect(onClose).toHaveBeenCalled()
  })
})

describe("Date and time formatting", () => {
  it("does not shift date-only meeting dates by the local time zone", () => {
    expect(formatDate("2026-08-03T00:00:00Z")).toBe(new Date(Date.UTC(2026, 7, 3)).toLocaleDateString(undefined, { timeZone: "UTC" }))
  })

  it("makes the end-date filter include the whole day", () => {
    expect(endOfDayIso("2026-09-30")).toBe("2026-09-30T23:59:59.999Z")
  })

  it("never shows 60 seconds", () => {
    expect(formatDuration(119.6)).toBe("2m 00s")
  })
})
