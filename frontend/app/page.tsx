"use client";

import "./phase1.css";
import { AuthScreen } from "./auth-screen";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity, BookOpen, Check, ChevronRight, ClipboardCheck, FileSearch,
  FolderPlus, LayoutDashboard, MessageSquare, Plus, RefreshCw, Search,
  Settings, ShieldCheck, Trash2, Users, X
} from "lucide-react";

type Project = { id: string; title: string; research_question: string; status: string; role: string };
type Scope = { id: string; version: number; status: string; research_question: string; framework: string; population?: string; intervention?: string; comparison?: string; outcomes?: string; study_types?: string; inclusion_criteria: string[]; exclusion_criteria: string[]; change_note?: string };
type Task = { id: string; artifact_type: string; status: string; resolution?: string; comment?: string };
type Audit = { id: string; action: string; actor_id: string; created_at: string };
type Member = { user_id: string; email: string; display_name: string; role: string };
type User = { id: string; email: string; display_name: string };

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/backend${path}`, {
    ...init,
    credentials: "include",
    headers: { ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }), ...init?.headers },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || `Request failed (${response.status})`);
  }
  return response.json();
}

const nav = [
  ["overview", LayoutDashboard, "Overview"], ["scope", BookOpen, "Plan & Scope"],
  ["discover", Search, "Discover"], ["papers", FileSearch, "Review Papers"],
  ["tasks", ClipboardCheck, "Review Tasks"], ["team", Users, "Team"], ["activity", Activity, "Activity"]
] as const;

export default function Workspace() {
  const [user, setUser] = useState<User | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState("");
  const [view, setView] = useState("overview");
  const [scopes, setScopes] = useState<Scope[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [audit, setAudit] = useState<Audit[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [error, setError] = useState("");
  const [newProject, setNewProject] = useState(false);
  const [scopeForm, setScopeForm] = useState(false);
  const [memberForm, setMemberForm] = useState(false);
  const [copilotOpen, setCopilotOpen] = useState(true);
  const [notice, setNotice] = useState("");

  useEffect(() => { api<User>("/auth/me").then(setUser).catch(() => setUser(null)).finally(() => setAuthLoading(false)); }, []);

  if (authLoading) return <div className="authLoading">Loading your workspace…</div>;
  if (!user) return <AuthScreen onAuthenticated={setUser}/>;

  const project = projects.find((item) => item.id === projectId);
  const latestScope = scopes[0];

  const loadProjects = useCallback(async () => {
    try {
      const data = await api<Project[]>("/workspace/projects");
      setProjects(data);
      setProjectId((current) => current || data[0]?.id || "");
    } catch (err) { setError(String(err)); }
  }, []);

  const loadProjectData = useCallback(async () => {
    if (!projectId) return;
    try {
      const [scopeData, taskData, auditData, memberData] = await Promise.all([
        api<Scope[]>(`/workspace/projects/${projectId}/scopes`),
        api<Task[]>(`/workspace/projects/${projectId}/tasks`),
        api<Audit[]>(`/workspace/projects/${projectId}/audit`),
        api<Member[]>(`/workspace/projects/${projectId}/members`),
      ]);
      setScopes(scopeData); setTasks(taskData); setAudit(auditData); setMembers(memberData); setError("");
    } catch (err) { setError(String(err)); }
  }, [projectId]);

  useEffect(() => { loadProjects(); }, [loadProjects]);
  useEffect(() => { loadProjectData(); }, [loadProjectData]);

  const progress = useMemo(() => latestScope?.status === "approved" ? 20 : latestScope ? 10 : 4, [latestScope]);

  async function createProject(form: FormData) {
    const created = await api<Project>("/workspace/projects", { method: "POST", body: JSON.stringify({ title: form.get("title"), research_question: form.get("question") }) });
    setNewProject(false); await loadProjects(); setProjectId(created.id); setNotice("Project created. Start by defining and approving its research scope.");
  }

  async function createScope(form: FormData) {
    const lines = (value: FormDataEntryValue | null) => String(value || "").split("\n").map(x => x.trim()).filter(Boolean);
    await api(`/workspace/projects/${projectId}/scopes`, { method: "POST", body: JSON.stringify({
      research_question: form.get("question"), framework: form.get("framework"), population: form.get("population") || null,
      intervention: form.get("intervention") || null, outcomes: form.get("outcomes") || null, study_types: form.get("study_types") || null,
      languages: ["English"], inclusion_criteria: lines(form.get("inclusion")), exclusion_criteria: lines(form.get("exclusion"))
    }) });
    setScopeForm(false); await loadProjectData();
  }

  async function transition(action: "submit" | "approved" | "changes_requested") {
    if (!latestScope) return;
    const path = action === "submit" ? `submit` : `review`;
    const body = action === "submit" ? undefined : JSON.stringify({ decision: action, comment: action === "approved" ? "Approved in workspace" : "Please refine the criteria" });
    await api(`/workspace/projects/${projectId}/scopes/${latestScope.id}/${path}`, { method: "POST", body });
    await loadProjectData(); await loadProjects();
  }

  async function updateStatus(status: string) {
    await api(`/workspace/projects/${projectId}/status`, { method: "PATCH", body: JSON.stringify({ status }) });
    await loadProjects();
  }

  async function addMember(form: FormData) {
    await api(`/workspace/projects/${projectId}/members`, { method: "PUT", body: JSON.stringify({
      email: form.get("email"), role: form.get("role")
    }) });
    setMemberForm(false); await loadProjectData();
  }

  async function removeMember(userId: string) {
    if (!window.confirm("Remove this member from the project?")) return;
    await api(`/workspace/projects/${projectId}/members/${encodeURIComponent(userId)}`, { method: "DELETE" });
    await loadProjectData();
  }

  return <main className="shell">
    <aside className="sidebar">
      <div className="brand"><div className="brandMark">R</div><div><strong>Research</strong><span>Workspace</span></div></div>
      <button className="newButton" onClick={() => setNewProject(true)}><FolderPlus size={17}/> New project</button>
      <div className="sectionLabel">Projects</div>
      <div className="projectList">{projects.map(item => <button key={item.id} className={item.id === projectId ? "project active" : "project"} onClick={() => setProjectId(item.id)}><span>{item.title.slice(0,1).toUpperCase()}</span><div><strong>{item.title}</strong><small>{item.status}</small></div></button>)}</div>
      <div className="sidebarBottom"><button onClick={()=>setView("team")}><Users size={16}/> Team</button><button><Settings size={16}/> Settings</button><div className="user"><span>{user.display_name.slice(0,2).toUpperCase()}</span><div><strong>{user.display_name}</strong><small>{user.email}</small></div></div><button className="logoutButton" onClick={async()=>{await api("/auth/logout",{method:"POST"});setUser(null)}}>Sign out</button></div>
    </aside>

    <section className="workspace">
      <header className="topbar"><div><div className="breadcrumb"><span className="crumbHome">Research</span><ChevronRight size={14}/> <span>Projects</span><ChevronRight size={14}/> {project?.title || "Select a project"}</div><h1>{project?.title || "Research Workspace"}</h1></div><div className="topActions"><span className="secureBadge"><ShieldCheck size={14}/> Private workspace</span><button className="iconButton" onClick={loadProjectData} title="Refresh"><RefreshCw size={17}/></button><button className="copilotToggle" onClick={() => setCopilotOpen(!copilotOpen)}><MessageSquare size={17}/> Copilot</button></div></header>
      {error && <div className="errorBanner">{error}<button onClick={() => setError("")}><X size={15}/></button></div>}
      {notice && <div className="noticeBanner"><Check size={15}/>{notice}<button onClick={() => setNotice("")}><X size={15}/></button></div>}
      {project ? <div className="body">
        <nav className="projectNav">{nav.map(([id, Icon, label]) => <button key={id} className={view === id ? "selected" : ""} onClick={() => setView(id)}><Icon size={17}/>{label}{id === "tasks" && tasks.filter(x=>x.status === "open").length > 0 && <b>{tasks.filter(x=>x.status === "open").length}</b>}</button>)}</nav>
        <div className="content">
          {view === "overview" && <Overview project={project} scope={latestScope} tasks={tasks} progress={progress} setView={setView} onStatus={updateStatus}/>} 
          {view === "scope" && <ScopeView project={project} scope={latestScope} history={scopes} onNew={() => setScopeForm(true)} onTransition={transition}/>} 
          {view === "tasks" && <TaskView tasks={tasks}/>} 
          {view === "team" && <TeamView members={members} role={project.role} onAdd={()=>setMemberForm(true)} onRemove={removeMember}/>} 
          {view === "activity" && <ActivityView events={audit}/>} 
          {(view === "discover" || view === "papers") && <EmptyStage view={view}/>} 
        </div>
      </div> : <div className="empty"><div className="emptyGlyph"><FolderPlus size={28}/></div><span className="eyebrow">Your research workspace</span><h2>Create your first project</h2><p>Start with a focused research question. You can then define the scope, invite reviewers, and move into discovery.</p><button onClick={() => setNewProject(true)}><FolderPlus size={16}/> Create project</button><small className="emptyMeta">Private by default · Invite collaborators when ready</small></div>}
    </section>
    {copilotOpen && project && <Copilot project={project}/>} 
    {newProject && <Modal title="New research project" close={() => setNewProject(false)}><form action={createProject}><label>Project title<input name="title" required autoFocus/></label><label>Research question<textarea name="question" required rows={5}/></label><div className="modalActions"><button type="button" onClick={() => setNewProject(false)}>Cancel</button><button className="primary">Create project</button></div></form></Modal>}
    {memberForm && <Modal title="Add project member" close={() => setMemberForm(false)}><form action={addMember}><p className="formHelp">The member must create an account first. Add them using the same email they registered with.</p><label>Account email<input name="email" type="email" required autoFocus placeholder="reviewer@university.edu"/></label><label>Project role<select name="role"><option value="researcher">Researcher</option><option value="reviewer">Reviewer</option><option value="owner">Owner</option></select></label><div className="modalActions"><button type="button" onClick={() => setMemberForm(false)}>Cancel</button><button className="primary">Add member</button></div></form></Modal>}
    {scopeForm && project && <Modal title="Create scope version" close={() => setScopeForm(false)}><form action={createScope} className="scopeGrid"><label className="wide">Research question<textarea name="question" defaultValue={project.research_question} required rows={3}/></label><label>Framework<select name="framework"><option>freeform</option><option>PICO</option><option>SPIDER</option></select></label><label>Population / domain<input name="population"/></label><label>Intervention / exposure<input name="intervention"/></label><label>Outcomes<input name="outcomes"/></label><label>Study types<input name="study_types"/></label><label className="wide">Inclusion criteria<textarea name="inclusion" rows={4} placeholder="One criterion per line"/></label><label className="wide">Exclusion criteria<textarea name="exclusion" rows={4} placeholder="One criterion per line"/></label><div className="modalActions wide"><button type="button" onClick={() => setScopeForm(false)}>Cancel</button><button className="primary">Save draft</button></div></form></Modal>}
  </main>;
}

function Overview({ project, scope, tasks, progress, setView, onStatus }: { project: Project; scope?: Scope; tasks: Task[]; progress: number; setView: (v:string)=>void; onStatus:(s:string)=>void }) { return <><div className="pageHeading"><div><span className="eyebrow">Project overview</span><h2>{project.research_question}</h2></div><div className="lifecycle"><span className={`status ${project.status}`}>{project.status}</span>{project.role==="owner"&&project.status!=="archived"&&<select aria-label="Project status" value={project.status} onChange={e=>onStatus(e.target.value)}><option value="draft">Draft</option><option value="active">Active</option><option value="paused">Paused</option><option value="completed">Completed</option><option value="archived">Archived</option></select>}</div></div><div className="progressBlock"><div><strong>Review progress</strong><span>{progress}%</span></div><div className="progress"><i style={{width:`${progress}%`}}/></div><div className="steps"><span className="done">Scope</span><span>Discover</span><span>Screen</span><span>Evidence</span><span>Synthesize</span></div></div><section className="nextAction"><div className="actionIcon"><BookOpen size={21}/></div><div><span>Recommended next action</span><h3>{scope ? scope.status === "approved" ? "Prepare the first search strategy" : "Complete scope review" : "Define the research scope"}</h3><p>{scope ? `Scope version ${scope.version} is ${scope.status.replace("_", " ")}.` : "Create eligibility criteria before searching academic providers."}</p></div><button onClick={()=>setView("scope")}>Open scope <ChevronRight size={16}/></button></section><div className="metrics"><article><span>Scope</span><strong>{scope ? `v${scope.version}` : "Not created"}</strong><small>{scope?.status || "Required"}</small></article><article><span>Open tasks</span><strong>{tasks.filter(x=>x.status === "open").length}</strong><small>Human review queue</small></article><article><span>Papers</span><strong>0</strong><small>Discovery starts in Phase 2</small></article><article><span>Verified evidence</span><strong>0</strong><small>Evidence engine pending</small></article></div></> }

function ScopeView({ project, scope, history, onNew, onTransition }: {project:Project; scope?:Scope; history:Scope[]; onNew:()=>void; onTransition:(x:"submit"|"approved"|"changes_requested")=>void}) { const canNew=!scope||["approved","superseded"].includes(scope.status); return <><div className="pageHeading"><div><span className="eyebrow">Plan</span><h2>Research scope</h2><p>Versioned eligibility criteria define what the review can claim.</p></div>{canNew&&<button className="primary" onClick={onNew}><Plus size={16}/> New version</button>}</div>{scope ? <section className="scopeSheet"><div className="scopeHeader"><div><span>Version {scope.version}</span><strong>{scope.status.replace("_"," ")}</strong></div><ShieldCheck size={22}/></div><h3>{scope.research_question}</h3><div className="scopeFields"><Field label="Framework" value={scope.framework}/><Field label="Population / domain" value={scope.population}/><Field label="Intervention / exposure" value={scope.intervention}/><Field label="Outcomes" value={scope.outcomes}/><Field label="Study types" value={scope.study_types}/></div><Criteria title="Inclusion criteria" values={scope.inclusion_criteria}/><Criteria title="Exclusion criteria" values={scope.exclusion_criteria}/>{scope.change_note&&<div className="changeNote"><strong>Requested changes</strong>{scope.change_note}</div>}<div className="sheetActions">{scope.status==="draft"&&["owner","researcher"].includes(project.role)&&<button className="primary" onClick={()=>onTransition("submit")}>Submit for review</button>}{scope.status==="pending_review"&&["owner","reviewer"].includes(project.role)&&<><button onClick={()=>onTransition("changes_requested")}>Request changes</button><button className="primary" onClick={()=>onTransition("approved")}><Check size={16}/> Approve scope</button></>}</div></section>:<div className="emptyPanel"><BookOpen size={28}/><h3>No scope version</h3><p>Create the first scope to establish inclusion and exclusion boundaries.</p><button className="primary" onClick={onNew}>Create scope</button></div>} {history.length>1&&<section className="history"><h3>Version history</h3>{history.map(s=><div key={s.id}><span>v{s.version}</span><strong>{s.status}</strong><p>{s.research_question}</p></div>)}</section>}</> }
function Field({label,value}:{label:string;value?:string}) {return <div><span>{label}</span><strong>{value||"Not specified"}</strong></div>}
function Criteria({title,values}:{title:string;values:string[]}) {return <div className="criteria"><h4>{title}</h4>{values?.length?values.map((x,i)=><p key={i}><Check size={15}/>{x}</p>):<span>No criteria specified</span>}</div>}
function TaskView({tasks}:{tasks:Task[]}) {return <><div className="pageHeading"><div><span className="eyebrow">Review</span><h2>Human review queue</h2><p>Decisions that require explicit approval or changes.</p></div><span className="quietLabel">{tasks.filter(x=>x.status === "open").length} open</span></div><div className="table">{tasks.length?tasks.map(t=><div className="tableRow" key={t.id}><span className="rowIcon"><ClipboardCheck size={17}/></span><div><strong>{t.artifact_type} review</strong><small>{t.comment||"No reviewer comment"}</small></div><span className={`status ${t.status}`}>{t.resolution||t.status}</span></div>):<div className="emptyPanel compact"><div className="emptyGlyph"><ClipboardCheck size={24}/></div><h3>Review queue is clear</h3><p>Approval tasks will appear here when a scope or evidence artifact needs a decision.</p></div>}</div></>}
function TeamView({members,role,onAdd,onRemove}:{members:Member[];role:string;onAdd:()=>void;onRemove:(id:string)=>void}) {return <><div className="pageHeading"><div><span className="eyebrow">Access</span><h2>Project team</h2><p>Project-scoped roles control read and mutation access.</p></div>{role==="owner"&&<button className="primary" onClick={onAdd}><Plus size={16}/> Add member</button>}</div><div className="table">{members.map(m=><div className="tableRow memberRow" key={m.user_id}><Users size={18}/><div><strong>{m.display_name}</strong><small>{m.email} · {m.user_id}</small></div><div className="memberActions"><span className="status active">{m.role}</span>{role==="owner"&&m.user_id!=="local-owner"&&<button title="Remove member" onClick={()=>onRemove(m.user_id)}><Trash2 size={15}/></button>}</div></div>)}</div></>}
function ActivityView({events}:{events:Audit[]}) {return <><div className="pageHeading"><div><span className="eyebrow">Audit</span><h2>Project activity</h2><p>Immutable history of important mutations and decisions.</p></div><span className="quietLabel">{events.length} events</span></div><div className="timeline">{events.length ? events.map(e=><div key={e.id}><i/><time>{new Date(e.created_at).toLocaleString()}</time><strong>{e.action.replaceAll("."," ")}</strong><span>{e.actor_id}</span></div>) : <div className="emptyPanel compact"><div className="emptyGlyph"><Activity size={24}/></div><h3>No activity yet</h3><p>Project changes and review decisions will be recorded here.</p></div>}</div></>}
function EmptyStage({view}:{view:string}) {return <div className="emptyPanel stage"><FileSearch size={30}/><h3>{view==="discover"?"Academic discovery begins in Phase 2":"Paper screening begins after discovery"}</h3><p>The workspace foundation is ready; this stage is intentionally locked until its upstream artifact is approved.</p></div>}
function Copilot({project}:{project:Project}) {const [question,setQuestion]=useState("");const [answer,setAnswer]=useState("");const [busy,setBusy]=useState(false);async function ask(){if(!question.trim())return;setBusy(true);try{const r=await api<{answer:string}>("/chat/",{method:"POST",body:JSON.stringify({query:question,project_id:project.id})});setAnswer(r.answer)}catch(e){setAnswer(String(e))}finally{setBusy(false)}}return <aside className="copilot"><header><div><MessageSquare size={18}/><strong>Project Copilot</strong></div><span>Scoped to this project</span></header><div className="copilotBody">{answer?<div className="answer">{answer}</div>:<div className="copilotEmpty"><MessageSquare size={26}/><p>Ask about verified project sources. Copilot cannot approve artifacts.</p></div>}</div><footer><textarea value={question} onChange={e=>setQuestion(e.target.value)} placeholder="Ask within the project corpus"/><button onClick={ask} disabled={busy}>{busy?"…":<ChevronRight size={18}/>}</button></footer></aside>}
function Modal({title,close,children}:{title:string;close:()=>void;children:React.ReactNode}) {return <div className="overlay"><div className="modal"><header><h2>{title}</h2><button onClick={close}><X size={18}/></button></header>{children}</div></div>}
