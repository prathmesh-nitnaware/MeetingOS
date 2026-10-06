import React, { useCallback, useEffect, useId, useMemo, useState } from "react"
import { Link, useSearchParams } from "react-router-dom"
import { Cpu, FolderKanban, Network, Tag, Users } from "lucide-react"
import { Modal } from "../components/Modal"
import { Notice } from "../components/Notice"
import { Spinner } from "../components/Spinner"
import { StatusBadge } from "../components/StatusBadge"
import { api, type EntityDetailResponse, type EntityTimelineResponse, type GraphNode } from "../services/api"
import { formatDate, humanize } from "../utils/format"

// Must match packages/common/enums.py::EntityType
const ENTITY_TYPES = ["PERSON", "ORGANIZATION", "PROJECT", "TECHNOLOGY", "PRODUCT", "LOCATION", "DATE"]
const PAGE_SIZE = 60

const EntityIcon: React.FC<{ type?: string | null }> = ({ type }) => {
  switch ((type ?? "").toUpperCase()) {
    case "PERSON":
      return <Users size={16} className="text-accent-indigo" aria-hidden="true" />
    case "PROJECT":
      return <FolderKanban size={16} className="text-accent-emerald" aria-hidden="true" />
    case "TECHNOLOGY":
      return <Cpu size={16} className="text-accent-amber" aria-hidden="true" />
    default:
      return <Tag size={16} className="text-accent-sky" aria-hidden="true" />
  }
}

export const EntitiesList: React.FC = () => {
  const ids = useId()
  const [searchParams, setSearchParams] = useSearchParams()
  const [entities, setEntities] = useState<GraphNode[]>([])
  const [hasMore, setHasMore] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [typeFilter, setTypeFilter] = useState("")

  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [detail, setDetail] = useState<EntityDetailResponse | null>(null)
  const [timeline, setTimeline] = useState<EntityTimelineResponse | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState<string | null>(null)

  const loadEntities = useCallback(
    async (offset: number) => {
      setLoading(true)
      setError(null)
      try {
        const page = await api.listCanonicalEntities(typeFilter || undefined, PAGE_SIZE, offset)
        setEntities((prev) => (offset === 0 ? page : [...prev, ...page]))
        setHasMore(page.length === PAGE_SIZE)
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load entities.")
      } finally {
        setLoading(false)
      }
    },
    [typeFilter]
  )

  useEffect(() => {
    void loadEntities(0)
  }, [loadEntities])

  const openEntity = useCallback(async (entityId: string) => {
    setSelectedId(entityId)
    setDetail(null)
    setTimeline(null)
    setDetailError(null)
    setDetailLoading(true)
    // Load both independently so one failing part does not hide the other
    const [d, t] = await Promise.allSettled([api.getEntityDetail(entityId), api.getEntityTimeline(entityId)])
    if (d.status === "fulfilled") setDetail(d.value)
    else setDetailError(d.reason instanceof Error ? d.reason.message : "Could not load this entity.")
    if (t.status === "fulfilled") setTimeline(t.value)
    else if (d.status === "fulfilled") setDetailError("The entity's timeline could not be loaded.")
    setDetailLoading(false)
  }, [])

  // Deep link from the meeting page: /entities?focus=<entity id>
  useEffect(() => {
    const focus = searchParams.get("focus")
    if (focus) void openEntity(focus)
  }, [searchParams, openEntity])

  const closeEntity = () => {
    setSelectedId(null)
    if (searchParams.has("focus")) setSearchParams({}, { replace: true })
  }

  const neighbourNames = useMemo(
    () => new Map((detail?.related_entities ?? []).map((n) => [n.id, n.name])),
    [detail]
  )

  const timelineEmpty =
    !timeline ||
    (timeline.events.length === 0 &&
      timeline.decisions.length === 0 &&
      timeline.commitments.length === 0 &&
      timeline.issues.length === 0)

  return (
    <div className="entities-list-page">
      <header className="page-header">
        <div>
          <h1 className="page-title">Entities & Knowledge Graph</h1>
          <p className="page-subtitle">People, projects and technologies mentioned across your meetings.</p>
        </div>
        <div className="inline-field">
          <label className="form-label" htmlFor={`${ids}-type`}>Type</label>
          <select id={`${ids}-type`} className="form-select" value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
            <option value="">All types</option>
            {ENTITY_TYPES.map((t) => (
              <option key={t} value={t}>{humanize(t)}</option>
            ))}
          </select>
        </div>
      </header>

      {error && <Notice tone="error">{error}</Notice>}

      {loading && entities.length === 0 ? (
        <Spinner message="Mapping entities..." />
      ) : entities.length === 0 ? (
        <div className="card empty-state">
          <Network size={48} className="empty-state-icon" aria-hidden="true" />
          <p>No entities found yet. They are extracted automatically when meetings are ingested.</p>
        </div>
      ) : (
        <>
          <section className="entities-grid">
            {entities.map((ent) => (
              <button key={ent.id} type="button" className="card entity-card" onClick={() => void openEntity(ent.id)}>
                <div className="entity-card-top">
                  <span className="entity-type-badge">{ent.entity_type}</span>
                  <EntityIcon type={ent.entity_type} />
                </div>
                <h3 className="entity-name">{ent.name}</h3>
                <div className="entity-presence">
                  Mentioned in {ent.meeting_count} meeting{ent.meeting_count === 1 ? "" : "s"}
                </div>
              </button>
            ))}
          </section>
          {hasMore && (
            <div className="load-more">
              <button type="button" className="btn btn-outline" disabled={loading} onClick={() => void loadEntities(entities.length)}>
                {loading ? "Loading…" : "Load more"}
              </button>
            </div>
          )}
        </>
      )}

      <Modal isOpen={selectedId !== null} onClose={closeEntity} title={detail?.entity.name ?? "Entity"} wide>
        {detailLoading && <Spinner message="Loading entity..." />}
        {detailError && <Notice tone="error">{detailError}</Notice>}

        {!detailLoading && detail && (
          <div className="stack">
            <div className="card">
              <div className="entity-card-top">
                <span className="badge badge-queued">{detail.entity.entity_type}</span>
                <span className="muted">
                  In {detail.meetings_count} meeting{detail.meetings_count === 1 ? "" : "s"}
                </span>
              </div>
              <div className="chip-row">
                {detail.meeting_ids.map((mid, index) => (
                  <Link key={mid} to={`/meetings/${mid}`} className="chip" title={mid} onClick={closeEntity}>
                    Open meeting {index + 1}
                  </Link>
                ))}
              </div>
            </div>

            <div>
              <h4 className="form-label">Relationships</h4>
              {detail.relationships.length === 0 ? (
                <p className="muted">No relationships recorded for this entity.</p>
              ) : (
                <ul className="relation-list">
                  {detail.relationships.map((rel) => {
                    const outgoing = rel.source_entity_id === detail.entity.entity_id
                    const other = outgoing ? rel.target_entity_id : rel.source_entity_id
                    return (
                      <li key={rel.relation_id} className="graph-edge-card">
                        <span className="graph-relation-type">
                          {outgoing ? "" : "← "}
                          {humanize(rel.relationship_type)}
                          {outgoing ? " →" : ""}
                        </span>
                        <button type="button" className="link-evidence" onClick={() => void openEntity(other)}>
                          {neighbourNames.get(other) ?? other}
                        </button>
                      </li>
                    )
                  })}
                </ul>
              )}
            </div>

            {timeline && (
              <div>
                <h4 className="form-label">Related facts & events</h4>
                {timelineEmpty ? (
                  <p className="muted">No decisions, commitments, issues or events mention this entity.</p>
                ) : (
                  <div className="stack">
                    {timeline.decisions.map((d) => (
                      <div key={d.decision_id} className="fact-item accent-indigo">
                        <div className="fact-header">
                          <span className="kpi-label">Decision</span>
                          <StatusBadge status={d.status} />
                        </div>
                        <p>{d.subject}</p>
                      </div>
                    ))}
                    {timeline.commitments.map((c) => (
                      <div key={c.commitment_id} className="fact-item accent-emerald">
                        <div className="fact-header">
                          <span className="kpi-label">Commitment</span>
                          <StatusBadge status={c.status} />
                        </div>
                        <p>{c.description}</p>
                        {c.current_deadline && <p className="muted">Due {formatDate(c.current_deadline)}</p>}
                      </div>
                    ))}
                    {timeline.issues.map((i) => (
                      <div key={i.issue_id} className="fact-item accent-amber">
                        <div className="fact-header">
                          <span className="kpi-label">Issue</span>
                          <StatusBadge status={i.status} />
                        </div>
                        <p>{i.description}</p>
                      </div>
                    ))}
                    {timeline.events.map((e) => (
                      <div key={e.event_id} className="fact-item">
                        <div className="fact-header">
                          <span className="kpi-label">{humanize(e.event_type)}</span>
                          <span className="muted">{formatDate(e.occurred_at)}</span>
                        </div>
                        <p className="muted">In: {e.meeting_title || e.meeting_id}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}
export default EntitiesList
