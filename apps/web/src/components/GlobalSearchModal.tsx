import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Search, X, Video, CheckSquare, Target, Tag, ArrowRight, Loader2, Plus, Layers, BookOpen } from "lucide-react";
import { api, SearchResultItem } from "../services/api";

interface GlobalSearchModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const GlobalSearchModal: React.FC<GlobalSearchModalProps> = ({ isOpen, onClose }) => {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
      if (query.trim()) {
        performSearch(query);
      }
    } else {
      setQuery("");
      setResults([]);
    }
  }, [isOpen]);

  // Handle global keyboard shortcut
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        if (isOpen) onClose();
        else {
          // Open modal handled by App level listener
        }
      }
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  const performSearch = async (q: string) => {
    if (!q.trim()) {
      setResults([]);
      return;
    }
    setLoading(true);
    try {
      const res = await api.search(q.trim(), 20);
      setResults(res.results || []);
      setSelectedIndex(0);
    } catch {
      // search fallback
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setQuery(val);
    performSearch(val);
  };

  const handleSelectResult = (item: SearchResultItem) => {
    onClose();
    if (item.meeting_id) {
      navigate(`/meetings/${item.meeting_id}`);
    } else if (item.type === "action") {
      navigate("/action-items");
    } else if (item.type === "decision") {
      navigate("/decisions");
    } else {
      navigate(`/search?q=${encodeURIComponent(query)}`);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev < results.length - 1 ? prev + 1 : prev));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev > 0 ? prev - 1 : prev));
    } else if (e.key === "Enter" && results[selectedIndex]) {
      e.preventDefault();
      handleSelectResult(results[selectedIndex]);
    }
  };

  if (!isOpen) return null;

  const getTypeIcon = (type: string) => {
    switch (type) {
      case "meeting":
        return <Video size={14} className="text-accent" />;
      case "action":
        return <CheckSquare size={14} className="text-amber" />;
      case "decision":
        return <Target size={14} className="text-emerald" />;
      default:
        return <Tag size={14} className="text-indigo" />;
    }
  };

  return (
    <div className="search-modal-backdrop" onClick={onClose}>
      <div className="search-modal-container" onClick={(e) => e.stopPropagation()}>
        <div className="search-input-wrapper">
          <Search size={18} className="search-modal-icon" />
          <input
            ref={inputRef}
            type="text"
            className="search-modal-input"
            placeholder="Search meetings, transcripts, decisions, action items, topics..."
            value={query}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
          />
          {loading && <Loader2 size={16} className="spinner" />}
          <button type="button" className="btn-icon" onClick={onClose}>
            <X size={16} />
          </button>
        </div>

        <div className="search-modal-body">
          {query.trim() === "" ? (
            <div className="search-hints">
              <p className="search-hint-title" style={{ fontSize: "0.75rem", fontWeight: "700", textTransform: "uppercase", color: "#64748b", letterSpacing: "0.05em", marginBottom: "0.5rem" }}>
                Quick Navigation
              </p>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: "0.5rem", marginBottom: "1rem" }}>
                <button
                  type="button"
                  className="search-suggestion-item"
                  onClick={() => {
                    onClose();
                    navigate("/meetings/new");
                  }}
                >
                  <Plus size={13} className="text-brand-accent" /> New Meeting
                </button>
                <button
                  type="button"
                  className="search-suggestion-item"
                  onClick={() => {
                    onClose();
                    navigate("/projects");
                  }}
                >
                  <Layers size={13} className="text-indigo" /> Projects
                </button>
                <button
                  type="button"
                  className="search-suggestion-item"
                  onClick={() => {
                    onClose();
                    navigate("/action-items");
                  }}
                >
                  <CheckSquare size={13} className="text-amber" /> Actions
                </button>
                <button
                  type="button"
                  className="search-suggestion-item"
                  onClick={() => {
                    onClose();
                    navigate("/decisions");
                  }}
                >
                  <Target size={13} className="text-emerald" /> Decisions
                </button>
                <button
                  type="button"
                  className="search-suggestion-item"
                  onClick={() => {
                    onClose();
                    navigate("/knowledge");
                  }}
                >
                  <BookOpen size={13} className="text-accent" /> Knowledge
                </button>
              </div>

              <p className="search-hint-title" style={{ fontSize: "0.75rem", fontWeight: "700", textTransform: "uppercase", color: "#64748b", letterSpacing: "0.05em", marginBottom: "0.5rem" }}>
                Suggested Topics
              </p>
              <div className="search-suggestions-list">
                <button
                  type="button"
                  className="search-suggestion-item"
                  onClick={() => {
                    setQuery("Product Launch");
                    performSearch("Product Launch");
                  }}
                >
                  <Tag size={13} /> Product Launch
                </button>
                <button
                  type="button"
                  className="search-suggestion-item"
                  onClick={() => {
                    setQuery("API Architecture");
                    performSearch("API Architecture");
                  }}
                >
                  <Tag size={13} /> API Architecture
                </button>
                <button
                  type="button"
                  className="search-suggestion-item"
                  onClick={() => {
                    setQuery("Authentication");
                    performSearch("Authentication");
                  }}
                >
                  <Tag size={13} /> Authentication
                </button>
                <button
                  type="button"
                  className="search-suggestion-item"
                  onClick={() => {
                    setQuery("PostgreSQL");
                    performSearch("PostgreSQL");
                  }}
                >
                  <Tag size={13} /> PostgreSQL Migration
                </button>
              </div>
            </div>
          ) : results.length === 0 && !loading ? (
            <div className="search-empty">
              <p>No matching knowledge found for "{query}"</p>
              <span>Try searching for meeting topics, decisions, or participants.</span>
            </div>
          ) : (
            <div className="search-results-list">
              {results.map((item, idx) => (
                <div
                  key={`${item.type}-${item.id || idx}`}
                  className={`search-result-row ${idx === selectedIndex ? "selected" : ""}`}
                  onClick={() => handleSelectResult(item)}
                  onMouseEnter={() => setSelectedIndex(idx)}
                >
                  <div className="search-result-icon">{getTypeIcon(item.type)}</div>
                  <div className="search-result-info">
                    <div className="search-result-header">
                      <span className="search-result-title">{item.title}</span>
                      <span className="search-result-badge">{item.type}</span>
                    </div>
                    {item.snippet && <p className="search-result-snippet">{item.snippet}</p>}
                    {item.meeting_title && (
                      <span className="search-result-source">From: {item.meeting_title}</span>
                    )}
                  </div>
                  <ArrowRight size={14} className="search-result-arrow" />
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="search-modal-footer">
          <span><kbd>↑</kbd> <kbd>↓</kbd> Navigate</span>
          <span><kbd>↵</kbd> Select</span>
          <span><kbd>Esc</kbd> Close</span>
        </div>
      </div>
    </div>
  );
};

export default GlobalSearchModal;
