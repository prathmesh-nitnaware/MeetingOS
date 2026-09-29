import React, { useState, useEffect } from "react";
import { Search, Plus, Sparkles, Building, User, Command } from "lucide-react";
import { useNavigate } from "react-router-dom";

interface HeaderProps {
  onOpenSearch: () => void;
  onOpenNewMeeting?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onOpenSearch, onOpenNewMeeting }) => {
  const navigate = useNavigate();
  const [greeting, setGreeting] = useState("Good day");
  const [userName, setUserName] = useState("Alex");
  const [orgName, setOrgName] = useState("Acme Corp");

  useEffect(() => {
    const hour = new Date().getHours();
    if (hour < 12) setGreeting("Good morning");
    else if (hour < 18) setGreeting("Good afternoon");
    else setGreeting("Good evening");

    const savedOrg = localStorage.getItem("meetingos_org_name");
    if (savedOrg) setOrgName(savedOrg);
  }, []);

  const handleNewMeeting = () => {
    if (onOpenNewMeeting) {
      onOpenNewMeeting();
    } else {
      navigate("/meetings/new");
    }
  };

  const isMac = typeof window !== "undefined" && navigator.platform.toUpperCase().indexOf("MAC") >= 0;

  return (
    <header className="app-header">
      <div className="header-left">
        <div>
          <h2 className="header-greeting">
            {greeting}, <span className="header-username">{userName}</span>
          </h2>
          <p className="header-subtitle">Here's what is happening across your meetings and team knowledge.</p>
        </div>
      </div>

      <div className="header-right">
        {/* Global Search Bar (Cmd+K) */}
        <button
          type="button"
          className="header-search-trigger"
          onClick={onOpenSearch}
          title="Search across all meetings and knowledge (Ctrl+K or ⌘K)"
        >
          <Search size={15} className="search-icon" />
          <span className="search-placeholder">Search meetings, decisions, actions...</span>
          <span className="search-kbd-badge">
            <Command size={11} /> {isMac ? "K" : "Ctrl+K"}
          </span>
        </button>

        {/* Org Switcher Pill */}
        <div className="header-org-pill" title="Current Active Workspace">
          <Building size={14} className="text-accent" />
          <span>{orgName}</span>
        </div>

        {/* Primary CTA: + New Meeting */}
        <button
          type="button"
          className="btn btn-primary btn-header-cta"
          onClick={handleNewMeeting}
        >
          <Plus size={16} />
          <span>New Meeting</span>
        </button>

        {/* User Profile Avatar */}
        <div className="header-avatar" title={`${userName} (${orgName})`}>
          <span>{userName.charAt(0)}</span>
        </div>
      </div>
    </header>
  );
};

export default Header;
