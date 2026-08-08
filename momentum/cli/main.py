import sys
import os
import json
import time
import subprocess
from pathlib import Path
from typing import Optional
from datetime import datetime

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich import box
from rich.panel import Panel
from rich.text import Text

app = typer.Typer(
    name="momentum",
    help="MOMENTUM — Local AI Developer Workflow Discovery Daemon",
    add_completion=False,
    no_args_is_help=True,
)

console = Console()

def _ensure_db():
    from momentum.database.base import init_db
    init_db()

def _get_state() -> dict:
    from momentum.daemon.state import daemon_state
    return daemon_state.get()

def _get_env_display() -> str:
    from momentum.config.settings import settings
    return settings.MOMENTUM_DB

@app.command()
def start(
    background: bool = typer.Option(False, "--background", "-b", help="Run in background"),
):
    """Start the MOMENTUM observation daemon."""
    _ensure_db()
    state = _get_state()
    if state.get("status") == "running":
        pid = state.get("pid", "?")
        console.print(f"[yellow]MOMENTUM is already running (PID {pid})[/yellow]")
        raise typer.Exit(1)

    console.print(Panel.fit(
        "[bold cyan]MOMENTUM[/bold cyan]\n[dim]Starting observation daemon...[/dim]",
        border_style="cyan",
    ))

    from momentum.daemon.state import daemon_state

    if background:
        proc = subprocess.Popen(
            [sys.executable, "-m", "momentum", "start"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        time.sleep(1.5)
        daemon_state.set_running(proc.pid)
        console.print(f"[green]✓[/green] MOMENTUM started in background (PID {proc.pid})")
        console.print(f"[dim]Observation database: {_get_env_display()}[/dim]")
        console.print("[dim]Run [bold]python -m momentum status[/bold] to check progress.[/dim]")
    else:
        from momentum.daemon.daemon import run_daemon
        console.print("[bold green]✓ MOMENTUM daemon running[/bold green]")
        console.print(f"[dim]API: http://127.0.0.1:8000/docs[/dim]")
        run_daemon()

@app.command()
def stop():
    """Stop the MOMENTUM daemon."""
    state = _get_state()
    status = state.get("status", "stopped")

    if status != "running":
        console.print("[yellow]MOMENTUM is not running[/yellow]")
        raise typer.Exit(0)

    pid = state.get("pid")
    if pid:
        try:
            import signal
            os.kill(int(pid), signal.SIGTERM)
            time.sleep(0.5)
            console.print(f"[green]✓[/green] Sent stop signal to PID {pid}")
        except (ProcessLookupError, PermissionError, OSError):
            pass

    from momentum.daemon.state import daemon_state
    daemon_state.set_stopped()
    console.print("[bold red]■[/bold red] MOMENTUM stopped")

@app.command()
def restart():
    """Restart the MOMENTUM daemon."""
    stop()
    time.sleep(1)
    start()

@app.command()
def status():
    """Show MOMENTUM daemon status and observation progress."""
    from momentum.database.event_store import count_events
    from momentum.sessions.sessionizer import count_sessions
    from momentum.discovery.workflow_builder import get_all_workflows
    from momentum.discovery.opportunity_engine import get_all_opportunities
    from momentum.learning.bandit import get_bandit
    from momentum.daemon.state import daemon_state
    from momentum.privacy.manager import privacy_manager

    _ensure_db()

    state = daemon_state.get()
    daemon_status = state.get("status", "stopped")
    day_num, day_total = daemon_state.get_day_progress()
    started_at = state.get("started_at", "—")
    pid = state.get("pid", "—")

    bandit = get_bandit()
    priv_paused = privacy_manager.is_paused()

    status_color = "green" if daemon_status == "running" else ("yellow" if daemon_status == "paused" else "red")
    status_icon = "●" if daemon_status == "running" else ("◌" if daemon_status == "paused" else "○")

    console.print()
    console.print(Panel(
        f"[{status_color}]{status_icon} {daemon_status.upper()}[/{status_color}]",
        title="[bold cyan]MOMENTUM[/bold cyan]",
        border_style="cyan",
        expand=False,
    ))

    table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
    table.add_column("Key", style="dim")
    table.add_column("Value", style="bold")

    table.add_row("PID", str(pid))
    table.add_row("Started", started_at[:19] if len(str(started_at)) >= 19 else str(started_at))
    table.add_row("Observation", f"Day {day_num}/{day_total}")
    table.add_row("Privacy", "[yellow]PAUSED[/yellow]" if priv_paused else "[green]collecting[/green]")
    table.add_row("Events collected", f"{count_events():,}")
    table.add_row("Sessions identified", f"{count_sessions():,}")
    table.add_row("Workflows discovered", str(len(get_all_workflows())))
    table.add_row("Opportunities found", str(len(get_all_opportunities())))
    table.add_row("Policy version", str(bandit.version))
    table.add_row("Policy epsilon", f"{bandit.epsilon:.3f}")
    table.add_row("Avg reward (last 20)", f"{bandit.get_average_reward(20):.3f}")

    console.print(table)
    console.print()

@app.command()
def evaluate(
    num_sessions: int = typer.Option(100, help="Number of benchmark sessions to generate"),
    seed: int = typer.Option(42, help="Random seed for deterministic generation"),
):
    """Evaluate clustering performance against a synthetic labeled dataset."""
    from momentum.evaluation.benchmark_generator import BenchmarkGenerator
    from momentum.evaluation.cluster_eval import evaluate_clusters
    from momentum.discovery.clusterer import cluster_sessions

    console.print(f"[cyan]Generating benchmark dataset with {num_sessions} sessions...[/cyan]")
    gen = BenchmarkGenerator(seed=seed)
    sessions, labels = gen.generate_dataset(num_sessions=num_sessions)

    console.print("[cyan]Running DBSCAN clustering...[/cyan]")
    sequences, cluster_groups, embeddings, valid_indices = cluster_sessions(
        sessions, eps=0.35, min_samples=3
    )

    console.print("[cyan]Computing evaluation metrics...[/cyan]")
    metrics = evaluate_clusters(labels, cluster_groups, valid_indices, len(sessions))

    table = Table(title="Clustering Evaluation Metrics", box=box.SIMPLE)
    table.add_column("Metric", style="dim")
    table.add_column("Score", style="bold green")

    table.add_row("Adjusted Rand Index (ARI)", f"{metrics.get('ari', 0.0):.3f}")
    table.add_row("Normalized Mutual Info (NMI)", f"{metrics.get('nmi', 0.0):.3f}")
    table.add_row("Cluster Purity", f"{metrics.get('purity', 0.0):.3f}")
    table.add_row("Signal Coverage", f"{metrics.get('coverage', 0.0):.3f}")
    table.add_row("Noise Rate", f"{metrics.get('noise_rate', 0.0):.3f}")
    table.add_row("Discovered Clusters", str(metrics.get("n_clusters", 0)))

    console.print(table)

@app.command()
def benchmark(
    num_sessions: int = typer.Option(200, help="Number of benchmark sessions to generate"),
    seed: int = typer.Option(42, help="Random seed for deterministic generation"),
):
    """Compare TF-IDF unigram vs n-gram clustering baselines."""
    from momentum.evaluation.benchmark_generator import BenchmarkGenerator
    from momentum.evaluation.baselines import run_clustering_pipeline
    from momentum.evaluation.cluster_eval import evaluate_clusters

    console.print(f"[cyan]Generating benchmark dataset with {num_sessions} sessions...[/cyan]")
    gen = BenchmarkGenerator(seed=seed)
    sessions, labels = gen.generate_dataset(num_sessions=num_sessions)

    table = Table(title="Clustering Baseline Comparison", box=box.SIMPLE)
    table.add_column("Metric", style="dim")
    table.add_column("TF-IDF Unigram", style="bold blue")
    table.add_column("TF-IDF N-gram", style="bold magenta")

    results = {}
    for baseline in ["tfidf_unigram", "tfidf_ngram"]:
        console.print(f"[cyan]Running {baseline} pipeline...[/cyan]")
        cluster_groups, valid_indices = run_clustering_pipeline(
            sessions, encoder_type=baseline, eps=0.35, min_samples=3
        )
        metrics = evaluate_clusters(labels, cluster_groups, valid_indices, len(sessions))
        results[baseline] = metrics
        
    m1 = results["tfidf_unigram"]
    m2 = results["tfidf_ngram"]

    table.add_row("ARI", f"{m1.get('ari', 0.0):.3f}", f"{m2.get('ari', 0.0):.3f}")
    table.add_row("NMI", f"{m1.get('nmi', 0.0):.3f}", f"{m2.get('nmi', 0.0):.3f}")
    table.add_row("Purity", f"{m1.get('purity', 0.0):.3f}", f"{m2.get('purity', 0.0):.3f}")
    table.add_row("Coverage", f"{m1.get('coverage', 0.0):.3f}", f"{m2.get('coverage', 0.0):.3f}")
    table.add_row("Noise Rate", f"{m1.get('noise_rate', 0.0):.3f}", f"{m2.get('noise_rate', 0.0):.3f}")
    table.add_row("Clusters", str(m1.get("n_clusters", 0)), str(m2.get("n_clusters", 0)))

    console.print()
    console.print(table)

@app.command()
def policy_eval(
    steps: int = typer.Option(1000, help="Number of simulated steps for evaluation"),
):
    """Evaluate bandit policy against heuristics using simulated rewards."""
    from momentum.evaluation.bandit_eval import simulate_environment
    
    console.print(f"[cyan]Simulating environment for {steps} steps...[/cyan]")
    summary = simulate_environment(num_steps=steps)
    
    table = Table(title="Policy Evaluation Results", box=box.SIMPLE)
    table.add_column("Policy", style="bold cyan")
    table.add_column("Cumulative Reward", justify="right")
    table.add_column("Precision", justify="right")
    table.add_column("Success Rate", justify="right")
    table.add_column("Unsafe Rate", justify="right", style="red")
    
    for policy_name, metrics in summary.items():
        table.add_row(
            policy_name.replace("_", " ").title(),
            f"{metrics['cumulative_reward']:.1f}",
            f"{metrics['recommendation_precision']:.1%}",
            f"{metrics['success_rate']:.1%}",
            f"{metrics['unsafe_action_rate']:.1%}"
        )
        
    console.print()
    console.print(table)

@app.command()
def pause():
    """Pause observation (MOMENTUM stops collecting data)."""
    from momentum.privacy.manager import privacy_manager
    from momentum.daemon.state import daemon_state
    privacy_manager.pause()
    daemon_state.set_paused()
    console.print("[yellow]⏸[/yellow]  Observation paused. Run [bold]python -m momentum resume[/bold] to continue.")

@app.command()
def resume():
    """Resume observation after pause."""
    from momentum.privacy.manager import privacy_manager
    from momentum.daemon.state import daemon_state
    privacy_manager.resume()
    daemon_state.set_resumed()
    console.print("[green]▶[/green]  Observation resumed.")

@app.command()
def report():
    """Generate the 7-day observation report."""
    from momentum.reporting.report_generator import generate_report
    from momentum.daemon.state import daemon_state

    _ensure_db()

    obs_start = daemon_state.get_observation_start()
    obs_end = datetime.utcnow()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        task = progress.add_task("Generating report...", total=None)
        text = generate_report(observation_start=obs_start, observation_end=obs_end)

    console.print(text)

@app.command()
def opportunities():
    """List discovered automation opportunities."""
    from momentum.discovery.opportunity_engine import get_all_opportunities

    _ensure_db()
    opps = get_all_opportunities()

    if not opps:
        console.print("[dim]No automation opportunities found yet.[/dim]")
        console.print("[dim]Run [bold]python -m momentum simulate[/bold] to generate data.[/dim]")
        return

    table = Table(
        title="[bold cyan]Automation Opportunities[/bold cyan]",
        box=box.ROUNDED,
        show_lines=True,
    )
    table.add_column("#", style="dim", width=3)
    table.add_column("Name", min_width=30, max_width=40)
    table.add_column("Score", justify="right", width=7)
    table.add_column("Conf", justify="right", width=6)
    table.add_column("Freq/wk", justify="right", width=8)
    table.add_column("Hrs/wk", justify="right", width=8)
    table.add_column("Risk", width=8)
    table.add_column("ID", style="dim", min_width=12)

    risk_colors = {"Low": "green", "Medium": "yellow", "High": "red"}

    for i, opp in enumerate(opps, 1):
        risk_color = risk_colors.get(opp.risk_level, "white")
        table.add_row(
            str(i),
            opp.name,
            f"{opp.automation_score:.0f}/100",
            f"{opp.confidence:.0%}",
            f"{opp.frequency:.1f}",
            f"{opp.estimated_weekly_minutes / 60:.1f}h",
            f"[{risk_color}]{opp.risk_level}[/{risk_color}]",
            opp.id[:12] + "...",
        )

    console.print()
    console.print(table)
    console.print()
    console.print("[dim]Use [bold]python -m momentum inspect <id>[/bold] to inspect an opportunity.[/dim]")
    console.print("[dim]Use [bold]python -m momentum approve <id>[/bold] to approve.[/dim]")
    console.print()

@app.command()
def inspect(
    opportunity_id: str = typer.Argument(..., help="Opportunity or workflow ID to inspect"),
):
    """Inspect a workflow or automation opportunity in detail."""
    from momentum.discovery.opportunity_engine import get_opportunity_by_id
    from momentum.discovery.workflow_builder import get_workflow_by_id
    from momentum.reporting.report_generator import format_workflow_for_inspect
    from momentum.agents.interpreter_agent import interpret_workflow

    _ensure_db()

    opp = get_opportunity_by_id(opportunity_id)
    if opp is None:
        wf_direct = get_workflow_by_id(opportunity_id)
        if wf_direct:
            console.print(format_workflow_for_inspect(wf_direct))
            return
        console.print(f"[red]No opportunity or workflow found with ID: {opportunity_id}[/red]")
        raise typer.Exit(1)

    workflow = get_workflow_by_id(opp.workflow_id)
    if not workflow:
        console.print(f"[red]Workflow not found for opportunity {opportunity_id}[/red]")
        raise typer.Exit(1)

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as prog:
        task = prog.add_task("Interpreting workflow...", total=None)
        interpretation = interpret_workflow(workflow)

    model_used = interpretation.get("model", "offline")
    console.print(f"[dim](Interpreted using: {model_used})[/dim]")
    console.print()
    console.print(format_workflow_for_inspect(workflow, opp))

    from momentum.discovery.opportunity_engine import explain_score
    from momentum.reporting.opportunity_formatter import format_opportunity_explanation
    console.print()
    explain_dict = explain_score(workflow)
    console.print(format_opportunity_explanation(explain_dict))

@app.command()
def approve(
    opportunity_id: str = typer.Argument(..., help="Opportunity ID to approve"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Gather context, generate an LLM automation plan, and activate."""
    from momentum.discovery.opportunity_engine import get_opportunity_by_id
    from momentum.discovery.workflow_builder import get_workflow_by_id
    from momentum.reporting.opportunity_formatter import format_approve_prompt
    from momentum.models.automation import AutomationRecord
    from momentum.models.opportunity import OpportunityRecord
    from momentum.database.base import get_db
    from momentum.agents.interpreter_agent import generate_automation_plan
    from momentum.agents.context_gatherer import gather_context
    import json

    _ensure_db()

    opp = get_opportunity_by_id(opportunity_id)
    if not opp:
        console.print(f"[red]No opportunity found with ID: {opportunity_id}[/red]")
        raise typer.Exit(1)

    workflow = get_workflow_by_id(opp.workflow_id)
    if not workflow:
        console.print(f"[red]Workflow not found[/red]")
        raise typer.Exit(1)

    console.print(format_approve_prompt(workflow, opp))
    user_context = gather_context(workflow)

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), transient=True) as prog:
        prog.add_task("Generating automation plan via LLM...", total=None)
        try:
            llm_plan = generate_automation_plan(workflow, user_context)
        except Exception as e:
            console.print(f"[red]Plan generation failed: {e}[/red]")
            raise typer.Exit(1)

    console.print()
    console.print(f"[dim](Generated by: {llm_plan.get('model', 'llm')})[/dim]")
    console.print()

    plan_table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
    plan_table.add_column("Key", style="dim", min_width=18)
    plan_table.add_column("Value", style="bold")
    plan_table.add_row("Automation name", llm_plan.get("name", workflow.name))
    plan_table.add_row("Description", llm_plan.get("description", ""))
    trigger_info = llm_plan.get("trigger", {})
    trigger_str = trigger_info.get("cron", trigger_info.get("event", trigger_info.get("type", "manual")))
    plan_table.add_row("Trigger", trigger_str)
    plan_table.add_row("Est. time saved", f"{llm_plan.get('estimated_time_saved_minutes', 0)} min/run")
    console.print(plan_table)

    steps = llm_plan.get("steps", [])
    if steps:
        console.print("\n[bold]Steps:[/bold]")
        for i, step in enumerate(steps, 1):
            confirm_flag = " [yellow][CONFIRM][/yellow]" if step.get("requires_confirmation") else ""
            critical_flag = " [red][CRITICAL][/red]" if step.get("critical") else ""
            console.print(f"  {i}. [cyan]{step['tool']}[/cyan] — {step.get('description', '')}{confirm_flag}{critical_flag}")

    risks = llm_plan.get("risks", [])
    if risks:
        console.print("\n[bold yellow]Risks:[/bold yellow]")
        for risk in risks:
            console.print(f"  [yellow]⚠[/yellow] {risk}")

    console.print()

    if not yes:
        confirmed = typer.confirm("Approve and activate this automation?", default=False)
        if not confirmed:
            console.print("[yellow]Approval cancelled.[/yellow]")
            raise typer.Exit(0)

    from uuid import uuid4
    auto_id = str(uuid4())
    tools_in_plan = [s["tool"] for s in steps]

    with get_db() as db:
        automation = AutomationRecord(
            id=auto_id,
            opportunity_id=opp.id,
            workflow_id=workflow.id,
            name=llm_plan.get("name", workflow.name),
            plan_json=json.dumps(llm_plan),
            tools_json=json.dumps(tools_in_plan),
            permissions_json=json.dumps(llm_plan.get("permissions_needed", [])),
            trigger_json=json.dumps(llm_plan.get("trigger", {})),
            conditions_json=json.dumps([]),
            confidence=opp.confidence,
            autonomy_level=3,
            status="active",
        )
        db.add(automation)

        opp_record = db.query(OpportunityRecord).filter(OpportunityRecord.id == opp.id).first()
        if opp_record:
            opp_record.status = "approved"
            opp_record.approved_at = datetime.utcnow()

    console.print(f"\n[bold green]✓ Automation activated![/bold green]")
    console.print(f"  ID     : [bold]{auto_id}[/bold]")
    console.print(f"  Name   : {llm_plan.get('name', workflow.name)}")
    console.print(f"  Status : active (autonomy level 3 — supervised)")
    console.print()
    console.print(f"[dim]Run [bold]python -m momentum run {auto_id}[/bold] to execute it now.[/dim]")
    console.print(f"[dim]Run [bold]python -m momentum automations[/bold] to list all automations.[/dim]")

@app.command()
def reject(
    opportunity_id: str = typer.Argument(..., help="Opportunity ID to reject"),
    reason: str = typer.Option("user_rejected", "--reason", "-r", help="Rejection reason"),
):
    """Reject an automation opportunity."""
    from momentum.models.opportunity import OpportunityRecord
    from momentum.database.base import get_db

    _ensure_db()

    with get_db() as db:
        opp = db.query(OpportunityRecord).filter(OpportunityRecord.id == opportunity_id).first()
        if not opp:
            console.print(f"[red]No opportunity found: {opportunity_id}[/red]")
            raise typer.Exit(1)
        opp.status = "rejected"
        opp.rejected_at = datetime.utcnow()
        opp.rejection_reason = reason
        opp.action_taken = "rejected"

    console.print(f"[yellow]✗[/yellow] Opportunity [bold]{opportunity_id[:16]}...[/bold] rejected.")

@app.command()
def automations():
    """List all active automations."""
    from momentum.database.base import get_db
    from momentum.models.automation import AutomationRecord

    _ensure_db()

    with get_db() as db:
        autos = db.query(AutomationRecord).all()

    if not autos:
        console.print("[dim]No automations found. Use [bold]python -m momentum approve <id>[/bold] to activate one.[/dim]")
        return

    table = Table(
        title="[bold cyan]Active Automations[/bold cyan]",
        box=box.ROUNDED,
        show_lines=True,
    )
    table.add_column("Name", min_width=25, max_width=35)
    table.add_column("Status", width=10)
    table.add_column("Confidence", justify="right", width=10)
    table.add_column("Autonomy", justify="right", width=9)
    table.add_column("Executions", justify="right", width=11)
    table.add_column("Success", justify="right", width=8)
    table.add_column("Time Saved", justify="right", width=11)
    table.add_column("ID", style="dim", width=14)

    status_colors = {"active": "green", "paused": "yellow", "disabled": "red"}

    for a in autos:
        sc = status_colors.get(a.status, "white")
        success_pct = f"{a.success_count / max(a.execution_count, 1):.0%}" if a.execution_count else "—"
        time_saved_h = f"{a.total_time_saved / 3600:.1f}h"
        table.add_row(
            a.name,
            f"[{sc}]{a.status}[/{sc}]",
            f"{a.confidence:.0%}",
            str(a.autonomy_level),
            str(a.execution_count),
            success_pct,
            time_saved_h,
            a.id[:12] + "...",
        )

    console.print()
    console.print(table)
    console.print()
    console.print("[dim]Use [bold]python -m momentum run <id>[/bold] to run an automation.[/dim]")

@app.command(name="run")
def run_automation(
    automation_id: str = typer.Argument(..., help="Automation ID to execute"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate without executing"),
):
    """Execute an automation."""
    from momentum.database.base import get_db
    from momentum.models.automation import AutomationRecord
    from momentum.discovery.workflow_builder import get_workflow_by_id
    from momentum.execution.executor import execute_automation
    from momentum.execution.outcome_recorder import record_and_learn

    _ensure_db()

    with get_db() as db:
        auto = db.query(AutomationRecord).filter(AutomationRecord.id == automation_id).first()
        if not auto:
            console.print(f"[red]Automation not found: {automation_id}[/red]")
            raise typer.Exit(1)
        auto_data = {
            "id": auto.id,
            "name": auto.name,
            "confidence": auto.confidence,
            "autonomy_level": auto.autonomy_level,
            "status": auto.status,
            "execution_count": auto.execution_count,
            "success_count": auto.success_count,
            "failure_count": auto.failure_count,
            "consecutive_failures": auto.consecutive_failures,
            "total_time_saved": auto.total_time_saved,
        }

    wf = get_workflow_by_id(auto.workflow_id) if auto else None
    wf_data = {
        "frequency": wf.frequency if wf else 5.0,
        "average_duration": wf.average_duration if wf else 300.0,
        "duration_variance": wf.duration_variance if wf else 60.0,
        "repetition_score": wf.repetition_score if wf else 0.5,
        "determinism_score": wf.determinism_score if wf else 0.6,
        "risk_score": wf.risk_score if wf else 0.3,
        "decision_points": wf.get_decision_points() if wf else [],
        "estimated_weekly_minutes": wf.estimated_weekly_minutes if wf else 60.0,
    } if wf else {}

    mode = "[yellow](DRY RUN)[/yellow]" if dry_run else "[cyan](LIVE)[/cyan]"
    console.print(f"\n[bold]Executing:[/bold] {auto.name} {mode}")

    with Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        TimeElapsedColumn(),
        transient=False,
    ) as progress:
        task = progress.add_task("Running automation tools...", total=None)
        outcome = execute_automation(auto, dry_run=dry_run)
        progress.update(task, completed=True)

    with get_db() as db:
        auto_fresh = db.query(AutomationRecord).filter(AutomationRecord.id == automation_id).first()

    if auto_fresh:
        learn_result = record_and_learn(outcome, auto_fresh, wf_data)
    else:
        learn_result = {"reward": 0.0, "confidence_after": auto.confidence, "autonomy_after": auto.autonomy_level}

    success_icon = "[green]✓[/green]" if outcome.success else "[red]✗[/red]"
    console.print(f"\n{success_icon} Execution {'succeeded' if outcome.success else 'failed'}")

    result_table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
    result_table.add_column("Key", style="dim")
    result_table.add_column("Value", style="bold")

    result_table.add_row("Success", "[green]Yes[/green]" if outcome.success else "[red]No[/red]")
    result_table.add_row("Execution time", f"{outcome.execution_time:.2f}s")
    result_table.add_row("Time saved", f"{outcome.time_saved:.0f}s ({outcome.time_saved/60:.1f} min)")
    result_table.add_row("Reward", f"{learn_result['reward']:+.3f}")
    result_table.add_row("Confidence", f"{outcome.confidence_before:.0%} → {learn_result['confidence_after']:.0%}")
    result_table.add_row("Autonomy level", f"{learn_result['autonomy_before']} → {learn_result['autonomy_after']}")

    if outcome.failure_reason:
        result_table.add_row("Failure reason", f"[red]{outcome.failure_reason}[/red]")

    console.print(result_table)
    console.print()

@app.command()
def learn():
    """Trigger a learning pass over all historical outcomes."""
    from momentum.learning.trainer import run_learning_from_history
    from momentum.learning.bandit import get_bandit

    _ensure_db()

    console.print("[cyan]Running learning pass over historical outcomes...[/cyan]")

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), transient=True) as prog:
        task = prog.add_task("Processing outcomes and updating policy...", total=None)
        result = run_learning_from_history()

    bandit = get_bandit()
    stats = bandit.get_stats()

    console.print(f"\n[bold green]✓ Learning complete[/bold green]")

    table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
    table.add_column("Key", style="dim")
    table.add_column("Value", style="bold")
    table.add_row("Outcomes processed", str(result.get("updates", 0)))
    table.add_row("Average reward", f"{result.get('average_reward', 0):.3f}")
    table.add_row("Policy version", str(stats["version"]))
    table.add_row("Epsilon (exploration)", f"{stats['epsilon']:.4f}")
    table.add_row("Avg reward (last 20)", f"{stats['average_reward_last_20']:.3f}")
    console.print(table)
    console.print()

@app.command()
def simulate(
    days: int = typer.Option(7, "--days", "-d", help="Number of days to simulate"),
    seed: int = typer.Option(42, "--seed", help="Random seed for reproducibility"),
    clean: bool = typer.Option(False, "--clean", help="Clear existing data before simulation"),
):
    """Simulate N days of developer activity and run the full discovery pipeline."""
    from momentum.simulation.runner import run_simulation
    from momentum.database.event_store import delete_all_events

    if clean:
        if typer.confirm("Clear all existing data?", default=False):
            _ensure_db()
            deleted = delete_all_events()
            console.print(f"[dim]Cleared {deleted} events[/dim]")
        else:
            console.print("[dim]Clean cancelled[/dim]")

    console.print(Panel.fit(
        f"[bold cyan]MOMENTUM Simulation[/bold cyan]\n[dim]{days}-day developer activity with embedded workflow patterns[/dim]",
        border_style="cyan",
    ))

    progress_messages = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        transient=False,
    ) as progress:
        task = progress.add_task("Initializing...", total=None)

        def on_progress(msg: str):
            progress_messages.append(msg)
            progress.update(task, description=msg)

        result = run_simulation(days=days, seed=seed, progress_callback=on_progress)

    console.print(f"\n[bold green]✓ Simulation complete[/bold green]\n")

    table = Table(show_header=False, box=box.ROUNDED, padding=(0, 2))
    table.add_column("Metric", style="dim")
    table.add_column("Value", style="bold cyan")

    table.add_row("Days simulated", str(result["days_simulated"]))
    table.add_row("Events generated", f"{result['events_generated']:,}")
    table.add_row("Sessions identified", str(result["sessions_created"]))
    table.add_row("Workflows discovered", str(result["workflows_discovered"]))
    table.add_row("Automation opportunities", str(result["opportunities_found"]))

    if result.get("top_opportunity"):
        table.add_row("Top opportunity", result["top_opportunity"])

    learning = result.get("learning", {})
    table.add_row("Policy updates", str(learning.get("policy_updates", 0)))
    table.add_row(
        "Avg reward change",
        f"{learning.get('initial_average_reward', 0):.3f} → {learning.get('final_average_reward', 0):.3f}",
    )

    console.print(table)

    if result.get("workflow_names"):
        console.print("\n[bold]Discovered workflows:[/bold]")
        for name in result["workflow_names"]:
            console.print(f"  [cyan]→[/cyan] {name}")

    console.print()
    console.print("[dim]Run [bold]python -m momentum opportunities[/bold] to see automation candidates.[/dim]")
    console.print("[dim]Run [bold]python -m momentum report[/bold] for the full 7-day report.[/dim]")
    console.print()

@app.command()
def privacy(
    action: str = typer.Argument("status", help="Action: status | pause | resume | exclude <app> | include <app>"),
    app_name: Optional[str] = typer.Argument(None, help="Application name for exclude/include"),
):
    """Manage privacy settings and observation controls."""
    from momentum.privacy.manager import privacy_manager

    if action == "status":
        config = privacy_manager.get_config()
        table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
        table.add_column("Setting", style="dim")
        table.add_column("Value", style="bold")

        table.add_row("Observation", "[red]PAUSED[/red]" if config.observation_paused else "[green]Active[/green]")
        table.add_row("Collect window titles", str(config.collect_window_titles))
        table.add_row("Collect terminal commands", str(config.collect_terminal_commands))
        table.add_row("Collect browser URLs", str(config.collect_browser_urls))
        table.add_row("Redact sensitive patterns", str(config.redact_sensitive_patterns))
        table.add_row("Excluded applications", ", ".join(config.excluded_applications[:5]) or "none")
        console.print()
        console.print(table)

    elif action == "pause":
        privacy_manager.pause()
        console.print("[yellow]⏸[/yellow]  Observation paused")

    elif action == "resume":
        privacy_manager.resume()
        console.print("[green]▶[/green]  Observation resumed")

    elif action == "exclude":
        if not app_name:
            console.print("[red]Provide an application name[/red]")
            raise typer.Exit(1)
        privacy_manager.exclude_application(app_name)
        console.print(f"[green]✓[/green] '{app_name}' excluded from observation")

    elif action == "include":
        if not app_name:
            console.print("[red]Provide an application name[/red]")
            raise typer.Exit(1)
        privacy_manager.include_application(app_name)
        console.print(f"[green]✓[/green] '{app_name}' re-included in observation")

    else:
        console.print(f"[red]Unknown action: {action}[/red]")
        console.print("[dim]Valid actions: status | pause | resume | exclude <app> | include <app>[/dim]")
        raise typer.Exit(1)

@app.command()
def reset(
    confirm: bool = typer.Option(False, "--confirm", help="Skip confirmation prompt"),
):
    """Reset all MOMENTUM data (irreversible)."""
    from momentum.database.event_store import delete_all_events
    from momentum.daemon.state import daemon_state
    from momentum.config.settings import settings
    from pathlib import Path

    if not confirm:
        confirmed = typer.confirm(
            "This will delete ALL observation data, sessions, workflows, and learned policies. Continue?",
            default=False,
        )
        if not confirmed:
            console.print("[dim]Reset cancelled[/dim]")
            raise typer.Exit(0)

    _ensure_db()
    deleted = delete_all_events()
    daemon_state.set_stopped()

    weights = settings.get_weights_path()
    if weights.exists():
        weights.unlink()

    faiss_base = settings.get_data_dir() / "workflow_index"
    for ext in [".faiss", ".meta"]:
        p = Path(str(faiss_base) + ext)
        if p.exists():
            p.unlink()

    console.print(f"[bold red]⚠[/bold red] Reset complete. Deleted {deleted} events and all learned data.")

if __name__ == "__main__":
    app()
