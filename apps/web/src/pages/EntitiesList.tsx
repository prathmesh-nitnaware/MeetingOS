import React, { useState, useEffect } from "react"
import { Link } from "react-router-dom"
import { api, GraphNode, EntityDetailResponse, EntityTimelineResponse } from "../services/api"
import { Spinner } from "../components/Spinner"
import { Modal } from "../components/Modal"
import {
  Network,
  Users,
  Calendar,
  AlertCircle,
  Tag,
  GitCommit,
  TrendingUp,
  Link2,
  FolderKanban,
  Cpu
} from "lucide-react"

export const EntitiesList: React.FC = () => {
  const [entities, setEntities] = useState<GraphNode[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [typeFilter, setTypeFilter] = useState("")

  // Detailed Modal states
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null)
  const [entityDetail, setEntityDetail] = useState<EntityDetailResponse | null>(null)
  const [entityTimeline, setEntityTimeline] = useState<EntityTimelineResponse | null>(null)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [isModalOpen, setIsModalOpen] = useState(false)

  const loadEntities = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await api.listCanonicalEntities(typeFilter || undefined, 100, 0)
      setEntities(data)
    } catch (err: any) {
      setError(err.message || "Failed to load canonical entities.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadEntities()
  }, [typeFilter])

  const handleEntityClick = async (entityId: string) => {
    setSelectedEntityId(entityId)
    setLoadingDetail(true)
    setIsModalOpen(true)
    try {
      const [detailRes, timelineRes] = await Promise.all([
        api.getEntityDetail(entityId),
        api.getEntityTimeline(entityId)
      ])
      setEntityDetail(detailRes)
      setEntityTimeline(timelineRes)
    } catch (err: any) {
      alert(`Failed to load entity details: ${err.message}`)
      setIsModalOpen(false)
    } finally {
      setLoadingDetail(false)
    }
  }

  const getEntityIcon = (type: string) => {
    switch (type.toUpperCase()) {
      case "PERSON":
        return <Users size={16} className="text-accent-indigo" />
      case "PROJECT":
        return <FolderKanban size={16} className="text-accent-emerald" />
      case "TECHNOLOGY":
        return <Cpu size={16} className="text-accent-amber" />
      default:
        return <Tag size={16} className="text-accent-sky" />
    }
  }

  if (loading) return <Spinner message="Mapping canonical entities..." />

  return (
    <div className="entities-list-page">
      <header className="page-header">
        <div>
          <h1 className="page-title">Canonical Entities & Knowledge Graph</h1>
          <p className="page-subtitle">Inspect resolved entities, aliases, relationships, and cross-meeting networks.</p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <span className="form-label" style={{ margin: 0 }}>Filter Type:</span>
          <select
            className="form-select"
            style={{ width: "180px" }}
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
          >
            <option value="">All Types</option>
            <option value="PERSON">PERSON</option>
            <option value="TECHNOLOGY">TECHNOLOGY</option>
            <option value="PROJECT">PROJECT</option>
            <option value="ORGANIZATION">ORGANIZATION</option>
            <option value="LOCATION">LOCATION</option>
          </select>
        </div>
      </header>

      {error && (
        <div className="error-state">
          <AlertCircle size={20} />
          <span>{error}</span>
        </div>
      )}

      {entities.length === 0 ? (
        <div className="card empty-state">
          <Network size={48} className="empty-state-icon" />
          <p>No canonical entities found in organizational memory.</p>
        </div>
      ) : (
        <section className="entities-grid">
          {entities.map((ent) => (
            <div key={ent.id} className="card entity-card" onClick={() => handleEntityClick(ent.id)}>
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span className="entity-type-badge">{ent.type}</span>
                  {getEntityIcon(ent.type)}
                </div>
                <h3 className="entity-name">{ent.name}</h3>
              </div>
              <div className="entity-presence" style={{ marginTop: "16px" }}>
                Mentioned in {ent.presence_count} meetings
              </div>
            </div>
          ))}
        </section>
      )}

      {/* Detailed Entity neighborhood modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => { setIsModalOpen(false); setEntityDetail(null); setEntityTimeline(null); }}
        title={`Entity Detail: ${selectedEntityId}`}
      >
        {loadingDetail && <Spinner message="Loading entity neighborhood, relations, and history..." />}
        
        {!loadingDetail && entityDetail && (
          <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
            {/* Metadata and aliases card */}
            <div className="card" style={{ padding: "16px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "12px" }}>
                <span className="badge badge-queued">{entityDetail.entity.entity_type}</span>
                <span style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
                  Present in {entityDetail.meetings_count} meetings
                </span>
              </div>
              <h2 className="entity-name" style={{ fontSize: "22px" }}>{entityDetail.entity.name}</h2>
              {entityDetail.entity.aliases && entityDetail.entity.aliases.length > 0 && (
                <div style={{ marginTop: "10px", fontSize: "13px", color: "var(--text-secondary)" }}>
                  <span style={{ fontWeight: 600 }}>Resolved Aliases:</span>{" "}
                  {entityDetail.entity.aliases.map((alias, i) => (
                    <span key={i} className="badge" style={{ backgroundColor: "rgba(255,255,255,0.05)", marginLeft: "6px", textTransform: "none" }}>
                      {alias}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Neighborhood Graph view */}
            <div>
              <h4 className="form-label" style={{ marginBottom: "10px" }}>Relational Neighborhood Graph</h4>
              <div className="graph-neighborhood">
                <div className="graph-root-node">{entityDetail.entity.name}</div>
                
                {entityDetail.relationships.length === 0 ? (
                  <p style={{ alignSelf: "center", fontSize: "12px", color: "var(--text-muted)", marginTop: "12px" }}>
                    No cross-meeting relationship links resolved for this node.
                  </p>
                ) : (
                  <div className="graph-edges-container">
                    {entityDetail.relationships.map((rel) => {
                      const isSource = rel.source_entity_id.toLowerCase() === entityDetail.entity.entity_id.toLowerCase()
                      const neighborId = isSource ? rel.target_entity_id : rel.source_entity_id
                      return (
                        <div key={rel.relation_id} className="graph-edge-card">
                          <span className="graph-relation-type">
                            {isSource ? "" : "← "}{rel.relationship_type}{isSource ? " →" : ""}
                          </span>
                          <span style={{ fontWeight: 600 }}>{neighborId}</span>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            </div>

            {/* Entity Timeline stream */}
            {entityTimeline && (
              <div>
                <h4 className="form-label" style={{ marginBottom: "10px" }}>Entity Lifecycle Timeline</h4>
                {entityTimeline.events.length === 0 && entityTimeline.decisions.length === 0 && entityTimeline.commitments.length === 0 ? (
                  <p style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                    No events tracked specifically for this entity.
                  </p>
                ) : (
                  <div className="timeline-stream" style={{ maxHeight: "300px", overflowY: "auto", padding: "10px" }}>
                    {entityTimeline.decisions.map((dec) => (
                      <div key={dec.decision_id} className="timeline-event modified">
                        <div className="timeline-node"></div>
                        <div className="card timeline-card" style={{ padding: "12px" }}>
                          <span className="timeline-type" style={{ color: "var(--accent-amber)", fontSize: "10px" }}>DECISION</span>
                          <p style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-primary)" }}>{dec.subject}</p>
                          <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>Status: {dec.status}</span>
                        </div>
                      </div>
                    ))}
                    {entityTimeline.commitments.map((com) => (
                      <div key={com.commitment_id} className="timeline-event detected">
                        <div className="timeline-node"></div>
                        <div className="card timeline-card" style={{ padding: "12px" }}>
                          <span className="timeline-type" style={{ color: "var(--accent-sky)", fontSize: "10px" }}>COMMITMENT</span>
                          <p style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-primary)" }}>{com.description}</p>
                          <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>Owner: {com.owner_id} • Status: {com.status}</span>
                        </div>
                      </div>
                    ))}
                    {entityTimeline.events.map((evt) => (
                      <div key={evt.event_id} className="timeline-event">
                        <div className="timeline-node"></div>
                        <div className="card timeline-card" style={{ padding: "12px" }}>
                          <span className="timeline-type" style={{ color: "var(--accent-indigo)", fontSize: "10px" }}>{evt.event_type}</span>
                          <p style={{ fontSize: "13px", color: "var(--text-primary)" }}>
                            Occurred in meeting <code>{evt.meeting_id}</code>
                          </p>
                        </div>
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
