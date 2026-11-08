const $ = (selector) => document.querySelector(selector);
let runs = [];
const STANDARD_EVALUATOR = "granite4.2:8b";
const STANDARD_MODE_NAMES = {smoke: "Smoke Test", single_pass: "Single-Pass Test", full: "Full Standard Benchmark"};
const STANDARD_MODES = {
  smoke: {
    cases: 2, budgetCount: 1, budgets: "2,048 tokens", categories: "2 smallest fixed tasks", repeat: 1,
    description: "Pipeline verification: runs the two smallest fixed tasks at the 2,048-token budget with one selected local answer model, each configuration exactly once (no repeats). Verifies execution, ASM integration, result storage, and reporting quickly; its results are not statistically meaningful.",
    note: "Smoke checks the pipeline at minimal cost; its results are not statistically meaningful.",
  },
  single_pass: {
    cases: 10, budgetCount: 5, budgets: "512, 1,024, 2,048, 4,096, 8,192 tokens", categories: "10 fixed tasks", repeat: 1,
    description: "Moderate evaluation: the normal 10-task workload at every standard budget with all local answer models, each benchmark configuration run exactly once. Preliminary only — a single run is not statistically robust.",
    note: "Single-pass results are preliminary: one run per condition is not statistically robust.",
  },
  full: {
    cases: 10, budgetCount: 5, budgets: "512, 1,024, 2,048, 4,096, 8,192 tokens", categories: "10 fixed tasks", repeat: 3,
    description: "Complete benchmark: the unchanged, previously recorded methodology with 3 repetitions per strategy and condition. Sequential local Ollama execution.",
    note: "This may take hours; runs are sequential and failed conditions are recorded while the suite continues.",
  },
};
let standardModelInfo = null;
let standardEvaluatorAvailable = false;

function esc(value) { return String(value ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c])); }
function fmt(value, digits = 2) { return value == null ? "—" : Number(value).toLocaleString(undefined, {maximumFractionDigits: digits}); }
async function api(path, options) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
  return data;
}
function switchPage(page) {
  document.querySelectorAll(".tab").forEach((tab) => tab.classList.toggle("active", tab.dataset.page === page));
  $("#benchmark-page").classList.toggle("hidden", page !== "benchmark");
  $("#results-page").classList.toggle("hidden", page !== "results");
  if (page === "results") { loadResults(); loadSystemEvents(); }
}
document.querySelectorAll(".tab").forEach((tab) => tab.addEventListener("click", () => switchPage(tab.dataset.page)));
$("#show-results").addEventListener("click", () => switchPage("results"));
$("#refresh").addEventListener("click", loadResults);
$("#refresh-system").addEventListener("click", loadSystemEvents);

async function init() {
  try {
    const [health, modelInfo] = await Promise.all([api("/api/health"), api("/api/models")]);
    const status = $("#service-status");
    status.textContent = modelInfo.available ? `Local backend ready · ${modelInfo.models.length} Ollama model(s)` : "Local backend ready · Ollama unavailable";
    status.classList.add(modelInfo.available ? "ok" : "bad");
    standardModelInfo = modelInfo;
    standardEvaluatorAvailable = modelInfo.models.includes(STANDARD_EVALUATOR);
    $("#standard-evaluator").textContent = standardEvaluatorAvailable ? `${STANDARD_EVALUATOR} (fixed; independent)` : `Required: ${STANDARD_EVALUATOR} not installed`;
    for (const model of modelInfo.models) {
      $("#model").insertAdjacentHTML("beforeend", `<option value="${esc(model)}">${esc(model)}</option>`);
      $("#evaluation-model").insertAdjacentHTML("beforeend", `<option value="${esc(model)}">${esc(model)}</option>`);
    }
    if (!health.status) throw new Error("Local backend did not report ready");
    updateStandardProfile();
    const currentJob = await api("/api/standard-benchmark");
    if (currentJob.status === "running") watchStandardJob(currentJob);
  } catch (error) {
    $("#service-status").textContent = `Backend unavailable · ${error.message}`;
    $("#service-status").classList.add("bad");
  }
}

function standardSmokeAnswerModel(models) {
  return models.find((model) => model !== STANDARD_EVALUATOR) || models[0] || null;
}

function standardEstimateText(mode) {
  const profile = STANDARD_MODES[mode];
  const models = standardModelInfo ? standardModelInfo.models : [];
  if (!standardModelInfo || !models.length || !standardEvaluatorAvailable) {
    return "No run will start until local models and the fixed evaluator are available.";
  }
  const answerModelCount = mode === "smoke" ? 1 : models.length;
  const selfCount = mode === "smoke"
    ? (standardSmokeAnswerModel(models) === STANDARD_EVALUATOR ? 1 : 0)
    : 1;
  const elementary = profile.cases * profile.budgetCount;
  const comparisons = answerModelCount * elementary;
  const strategyRuns = comparisons * profile.repeat * 2;
  const perRepeat = elementary * profile.repeat;
  const modelCalls = (answerModelCount - selfCount) * perRepeat * 5 + selfCount * perRepeat * 3;
  return `Estimated ${comparisons.toLocaleString()} task/budget/model comparisons, ${strategyRuns.toLocaleString()} strategy runs, and about ${modelCalls.toLocaleString()} local model calls. ${profile.note}`;
}

function updateStandardProfile() {
  const mode = $("#standard-mode").value;
  const profile = STANDARD_MODES[mode] || STANDARD_MODES.full;
  const models = standardModelInfo ? standardModelInfo.models : [];
  $("#standard-mode-description").textContent = profile.description;
  $("#standard-categories").textContent = profile.categories;
  $("#standard-budgets").textContent = profile.budgets;
  $("#standard-repetitions").textContent = `${profile.repeat} per strategy and condition`;
  $("#standard-model-count").textContent = models.length
    ? (mode === "smoke" ? `${models.length} detected · one selected answer model` : `${models.length} detected · all will run sequentially`)
    : "No local models available";
  $("#standard-estimate").textContent = standardEstimateText(mode);
  $("#run-standard-benchmark").disabled = !(models.length && standardEvaluatorAvailable);
}

function renderStandardJob(job) {
  const total = job.total_comparisons || 0;
  const completed = job.completed_comparisons || 0;
  const modeLabel = STANDARD_MODE_NAMES[job.mode] || "Standard benchmark";
  $("#standard-progress").value = total ? Math.round(completed * 100 / total) : 0;
  $("#standard-progress-text").textContent = job.status === "running"
    ? `${modeLabel}: ${completed}/${total} comparisons · ${job.responses || 0} answers · ${job.run_errors || 0} run errors · ${job.criterion_errors || 0} evaluator errors${job.current ? ` · ${job.current.model} / ${job.current.category} / ${fmt(job.current.context_budget,0)} tokens` : ""}`
    : job.status === "complete" || job.status === "completed_with_failures"
      ? `${modeLabel} ${job.status === "complete" ? "completed" : "completed with failures"}: ${completed}/${total} comparisons, ${job.responses || 0} answers, ${job.run_errors || 0} run errors. No model substitutions were made.`
      : job.status === "failed" ? `Job failed: ${job.error || "see stored job results"}` : job.status;
  $("#run-standard-benchmark").disabled = job.status === "running" || !$("#standard-model-count").textContent.includes("detected");
}

async function watchStandardJob(initialJob) {
  let job = initialJob;
  renderStandardJob(job);
  while (job.status === "running") {
    await new Promise((resolve) => setTimeout(resolve, 2000));
    job = await api(`/api/standard-benchmark/${encodeURIComponent(job.job_id)}`);
    renderStandardJob(job);
  }
  await loadResults();
}

$("#standard-mode").addEventListener("change", updateStandardProfile);
$("#run-standard-benchmark").addEventListener("click", async () => {
  const button = $("#run-standard-benchmark");
  const mode = $("#standard-mode").value;
  button.disabled = true;
  $("#standard-progress-text").textContent = `Starting ${STANDARD_MODE_NAMES[mode] || "standard"} profile…`;
  try {
    const job = await api("/api/standard-benchmark", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({mode})});
    await watchStandardJob(job);
  } catch (error) {
    $("#standard-progress-text").textContent = `Standard benchmark did not start or stopped: ${error.message}`;
    button.disabled = false;
  }
});

$("#run-model").addEventListener("change", (event) => {
  $("#model").disabled = !event.target.checked;
  $("#evaluation-model").disabled = !event.target.checked;
});
$("#experiment-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.currentTarget.querySelector("button[type=submit]");
  const repeat = Number($("#repeat").value);
  button.disabled = true;
  const created = [];
  let controlStatus = null;
  try {
    const strategy = $("#strategy").value;
    const payload = {
      source:$("#source").value, question:$("#question").value, strategy,
      criteria:$("#criteria").value,
      evaluation_model:$("#evaluation-model").value || null,
      expected_answer:$("#expected-answer").value || null, category:$("#category").value,
      expand_sources:$("#expand-sources").checked,
      context_budget:Number($("#budget").value), model:$("#model").value || null, run_model:$("#run-model").checked
    };
    if (strategy === "compare") {
      $("#progress").textContent = `Running ${repeat} paired repetitions…`;
      const comparison = await api("/api/compare", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({...payload, repeat_count:repeat})});
      created.push(...comparison.runs);
      controlStatus = comparison.equivalence.controls_match;
    } else {
      for (let i = 0; i < repeat; i++) {
        $("#progress").textContent = `Running ${i + 1} of ${repeat}…`;
        created.push(await api("/api/experiments", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(payload)}));
      }
    }
    $("#progress").textContent = `${created.length} run(s) saved.${controlStatus == null ? "" : ` Paired controls match: ${controlStatus}.`}`;
    showRun(created[created.length - 1]);
    await loadResults();
  } catch (error) { $("#progress").textContent = `Run failed: ${error.message}`; }
  finally { button.disabled = false; }
});

function showRun(run) {
  $("#latest-run").classList.remove("hidden");
  $("#run-detail").innerHTML = `<dl class="detail-grid">
    <dt>Run ID</dt><dd>${esc(run.run_id)}</dd><dt>Comparison</dt><dd>${esc(run.comparison_id ? "Paired comparison" : "Individual run")}</dd><dt>Strategy</dt><dd>${esc(strategyName(run.strategy))}</dd><dt>Compression mode</dt><dd>${esc(run.compression_mode || "None")}</dd>
    <dt>Context tokens</dt><dd>${fmt(run.metrics.final_assembled_context_tokens)} · ${esc(run.metrics.tokenizer)}</dd>
    <dt>Original tokens</dt><dd>${fmt(run.metrics.original_source_tokens)}</dd>
    <dt>ASM addresses</dt><dd>${fmt(run.metrics.addresses_retrieved)} retrieved / ${fmt(run.metrics.addresses_created)} created</dd>
    <dt>Answer</dt><dd>${run.response ? `<pre>${esc(run.response)}</pre>` : "Not run (offline preparation only)."}</dd>
    <dt>Evaluation</dt><dd>${run.evaluation ? `${esc(run.evaluation.method)}: ${esc(run.evaluation.score)}` : "Not scored"}</dd>
    <dt>Criterion evaluation</dt><dd>${run.criterion_evaluation?.status === "complete" ? `${fmt(run.criterion_evaluation.passed_count,0)} / ${fmt(run.criterion_evaluation.criteria_count,0)} passed · ${fmt(run.criterion_evaluation.pass_percentage)}% · evaluator ${esc(run.criterion_evaluation.model)}` : run.criterion_evaluation ? `${esc(run.criterion_evaluation.status)} · ${esc(run.criterion_evaluation.error || "No percentage available")}` : "No criteria supplied"}</dd>
    <dt>Error</dt><dd>${esc(run.error || "—")}</dd></dl><h3>Assembled context</h3><pre>${esc(run.context.context)}</pre>`;
}

async function loadResults() {
  try {
    const [experimentRuns, languageRuns, pressureRuns] = await Promise.all([
      api("/api/results"), api("/api/language-results"), api("/api/context-pressure-results")
    ]);
    runs = [...experimentRuns, ...pressureRuns, ...languageRuns];
    renderResults();
  }
  catch (error) { $("#results-body").innerHTML = `<tr><td colspan="9">Could not load results: ${esc(error.message)}</td></tr>`; }
}
function renderBars(target, rows, valueFn, labelFn, color = "#31a995") {
  const valid = rows.map((run) => ({run, value:valueFn(run)})).filter((item) => Number.isFinite(item.value));
  const max = Math.max(1, ...valid.map((item) => item.value));
  $(target).innerHTML = valid.length ? valid.map(({run,value}) => `<div class="bar-group"><span class="bar-value">${fmt(value)}</span><div class="bar" style="height:${Math.max(3, value / max * 110)}px;background:${color}"></div><span>${esc(labelFn(run))}</span></div>`).join("") : `<span class="status">No measured data yet.</span>`;
}
function renderQualityTokenChart(rows) {
  const points = rows.map((run) => ({run, score:run.exactTaskAverage, tokens:run.medianContext}))
    .filter((point) => Number.isFinite(point.score) && Number.isFinite(point.tokens));
  if (!points.length) { $("#quality-token-chart").textContent = "No measured data yet."; return; }
  const maxTokens = Math.max(1, ...points.map((point) => point.tokens));
  const circles = points.map(({run,score,tokens}) => {
    const x = 45 + (tokens / maxTokens) * 505;
    const y = 195 - Math.max(0, Math.min(1, score)) * 160;
    const color = run.strategy === "asm" ? "#31a995" : "#769ee8";
    return `<circle cx="${x}" cy="${y}" r="7" fill="${color}"><title>${esc(run.category)} · ${fmt(run.budget,0)} budget · ${esc(run.model)} · ${esc(strategyName(run.strategy))} · ${fmt(tokens,0)} median context tokens · task-average exact match ${fmt(score * 100)}%</title></circle>`;
  }).join("");
  $("#quality-token-chart").innerHTML = `<svg viewBox="0 0 600 240" role="img" aria-label="Answer exact-match score versus context token count"><line x1="45" y1="195" x2="565" y2="195" stroke="#718191"/><line x1="45" y1="25" x2="45" y2="195" stroke="#718191"/><text x="45" y="220" fill="#aebbc8">0</text><text x="510" y="220" fill="#aebbc8">${fmt(maxTokens,0)} tokens</text><text x="4" y="32" fill="#aebbc8">1.0</text><text x="7" y="194" fill="#aebbc8">0.0</text>${circles}</svg><small>● ASM &nbsp; ● Baseline</small>`;
}
function median(values) {
  const sorted = values.filter(Number.isFinite).sort((a,b) => a-b);
  if (!sorted.length) return null;
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}
function strategyName(value) { return value === "asm" ? "ASM" : value === "baseline" ? "No ASM (source-prefix baseline)" : value || "Not recorded"; }
function languageName(value) { return ({javascript:"JavaScript",c:"C",go:"Go",rust:"Rust"})[value] || value || "Not recorded"; }
function fixtureName(value) { return ({"small-factual":"Small factual","medium-numeric":"Medium numeric","large-multifact":"Large multifactor"})[value] || value || "Not recorded"; }
function revisionName(value) { return value?.startsWith("asm-bench-v") ? "Benchmark revision " + value.slice("asm-bench-v".length) : value || "Legacy"; }
function fieldName(value) {
  const known = {run_id:"Run ID",comparison_id:"Comparison ID",input_id:"Fixture",input_signature:"Input/settings signature",source_id:"Source ID",representation_id:"Representation ID",fixture_id:"Fixture",measurement_revision:"Benchmark revision",cpu_utilization_percent:"CPU utilization (%)",cpu_percent:"CPU utilization (%)",memory_bytes:"Memory (bytes)",elapsed_ns:"Elapsed time (ns)",execution_time_ns:"Execution time (ns)",execution_time_ms:"Execution time (ms)",process_wall_time_ns:"Process wall time (ns)",compile_time_ns:"Build time (ns)",temperature:"Temperature",seed:"Random seed",input_parse_ns:"Input parsing (ns)",retrieval_ns:"Retrieval (ns)",address_lookup_ns:"Address lookup (ns)",expansion_assembly_ns:"Expansion and assembly (ns)",serialization_ns:"Serialization (ns)"};
  if (known[value]) return known[value];
  return value.replace(/_/g, " ").replace(/\b[a-z]/g, (letter) => letter.toUpperCase()).replace(/\bId\b/g, "ID").replace(/\bAsm\b/g, "ASM").replace(/\bCpu\b/g, "CPU").replace(/\bNs\b/g, "ns").replace(/\bMs\b/g, "ms");
}
function readableValue(value) {
  if (value == null) return "Not measured";
  if (Array.isArray(value)) return value.length ? "<ul>" + value.map((item) => "<li>" + readableValue(item) + "</li>").join("") + "</ul>" : "None";
  if (typeof value === "object") return "<dl class='detail-grid'>" + Object.entries(value).map(([key,item]) => {
    const display = key === "strategy" ? strategyName(item) : key === "language" ? languageName(item) : key === "fixture_id" ? fixtureName(item) : key === "measurement_revision" ? revisionName(item) : item;
    return "<dt>" + esc(fieldName(key)) + "</dt><dd>" + readableValue(display) + "</dd>";
  }).join("") + "</dl>";
  return "<pre>" + esc(value) + "</pre>";
}
function displayRate(passed, total) { return total ? `${passed}/${total} · ${fmt(passed * 100 / total)}%` : "Not scored"; }
function renderAggregates(rows) {
  const html = groupModelProfiles(rows.filter((run) => !run.language_metrics)).map((group) => {
    const rubric = group.criteria.length
      ? `${group.criteria.length} criteria · ${group.evaluator}`
      : "No criteria supplied";
    const taskExact = group.exactTaskCount ? `${fmt(group.exactTaskAverage * 100)}% across ${group.exactTaskCount} scored task(s)` : "Not scored";
    const taskCriterion = group.criterionTaskCount ? `${fmt(group.criterionTaskAverage * 100)}% across ${group.criterionTaskCount} judged task(s)` : "Not scored";
    return `<tr><td>${esc(group.category)}</td><td>${fmt(group.budget,0)}</td><td>${esc(group.model)}${group.modelVersion ? `<small class="subline">${esc(group.modelVersion.slice(0,12))}</small>` : ""}</td><td>${esc(rubric)}</td><td>${esc(strategyName(group.strategy))}</td><td>${group.taskCount}</td><td>${group.runs.length} / ${group.responses}</td><td>${esc(taskExact)} <small class="subline">${displayRate(group.exactPassed,group.exactRuns.length)} of scored runs</small></td><td>${esc(taskCriterion)} <small class="subline">${displayRate(group.criteriaPassed,group.criteriaTotal)}</small></td><td>${fmt(group.medianContext,0)}</td><td>${fmt(group.medianModelTokens,0)}</td><td>${fmt(group.medianTime)} ms</td><td>${group.errors}</td></tr>`;
  });
  $("#aggregate-body").innerHTML = html.join("") || `<tr><td colspan="13">No stored model runs yet.</td></tr>`;
  const criterionRows = groupCriterionResults(rows.filter((run) => !run.language_metrics)).map((item) =>
    `<tr><td>${esc(item.category)}</td><td>${fmt(item.budget,0)}</td><td>${esc(item.model)}</td><td>${esc(strategyName(item.strategy))}</td><td>${esc(item.criterion)}</td><td>${item.tasks.size}</td><td>${item.passed}/${item.total} · ${fmt(item.passed * 100 / item.total)}%</td><td>${esc(item.evaluator)}</td></tr>`
  );
  $("#criterion-groups-body").innerHTML = criterionRows.join("") || `<tr><td colspan="8">No completed criterion judgments in stored runs.</td></tr>`;
  const languageRows = groupLanguageComparisons(rows).map((group) => {
    const delta = group.delta == null ? "No matched baseline" : group.delta < 0 ? `ASM faster ${fmt(Math.abs(group.delta))}%` : group.delta > 0 ? `ASM slower ${fmt(group.delta)}%` : "Same median";
    return `<tr><td>${esc(revisionName(group.revision))}</td><td>${esc(fixtureName(group.fixture))}</td><td>${esc(languageName(group.language))}</td><td>${group.asm.count} / ${group.baseline.count}</td><td>${fmt(group.asm.time,4)}</td><td>${fmt(group.baseline.time,4)}</td><td>${esc(delta)}</td><td>${fmt(group.asm.memory,0)} / ${fmt(group.baseline.memory,0)}</td><td>${group.asm.cpuCount} / ${group.baseline.cpuCount}</td></tr>`;
  });
  $("#language-summary-body").innerHTML = languageRows.join("") || `<tr><td colspan="9">No accepted language benchmark records.</td></tr>`;
}
function aggregateLanguageRuns(rows) {
  const groups = new Map();
  for (const run of rows) {
    const metric = run.language_metrics;
    if (!metric) continue;
    const normalizedMetric = {...metric, measurement_revision:metric.measurement_revision || run.measurement_revision || "legacy"};
    const key = `${normalizedMetric.measurement_revision}|${metric.fixture_id}|${metric.language}|${metric.strategy || "asm"}`;
    if (!groups.has(key)) groups.set(key, {metric:normalizedMetric, values:[], memoryValues:[], cpuValues:[], operationValues:{}});
    const group = groups.get(key);
    group.values.push(metric.execution_time_ms);
    if (Number.isFinite(metric.memory_bytes)) group.memoryValues.push(metric.memory_bytes);
    if (Number.isFinite(metric.cpu_utilization_percent)) group.cpuValues.push(metric.cpu_utilization_percent);
    for (const [name,value] of Object.entries(metric.operation_times_ns || {})) {
      if (!Number.isFinite(value)) continue;
      if (!group.operationValues[name]) group.operationValues[name] = [];
      group.operationValues[name].push(value);
    }
  }
  return [...groups.values()].map(({metric,values,memoryValues,cpuValues,operationValues}) => ({
    run_id:`${metric.measurement_revision || "legacy"}-${metric.fixture_id}-${metric.language}-${metric.strategy || "asm"}`,
    language_metrics:{...metric, execution_time_ms:median(values), memory_bytes:median(memoryValues), cpu_utilization_percent:median(cpuValues), operation_times_ns:Object.fromEntries(Object.entries(operationValues).map(([name,items]) => [name,median(items)])), repetitions:values.length}
  }));
}
function reportCriteria(run) {
  if (Array.isArray(run.criteria) && run.criteria.length) return run.criteria;
  return (run.criterion_evaluation?.criteria || []).map((item) => item.criterion).filter(Boolean);
}
function groupModelProfiles(rows) {
  const tasks = new Map();
  for (const run of rows) {
    const taskId = run.comparison_id || `individual:${run.run_id}`;
    if (!tasks.has(taskId)) tasks.set(taskId, {taskId, runs:[], first:run});
    tasks.get(taskId).runs.push(run);
  }
  const profiles = new Map();
  for (const task of tasks.values()) {
    const first = task.first;
    const criteria = reportCriteria(first);
    const profile = {
      category:first.category || "Uncategorized",
      budget:first.context_budget ?? null,
      model:first.model || "Offline preparation",
      modelVersion:first.model_version || "",
      evaluator:first.evaluation_model || "No evaluator recorded",
      evaluatorVersion:first.evaluation_model_version || "",
      criteria,
    };
    const key = JSON.stringify([profile.category,profile.budget,profile.model,profile.modelVersion,profile.evaluator,profile.evaluatorVersion,criteria]);
    if (!profiles.has(key)) profiles.set(key, {...profile, strategies:new Map()});
    const grouped = profiles.get(key);
    for (const run of task.runs) {
      if (!grouped.strategies.has(run.strategy || "unknown")) grouped.strategies.set(run.strategy || "unknown", new Map());
      const strategyTasks = grouped.strategies.get(run.strategy || "unknown");
      if (!strategyTasks.has(taskId)) strategyTasks.set(taskId, []);
      strategyTasks.get(taskId).push(run);
    }
  }
  const output = [];
  for (const profile of profiles.values()) for (const [strategy, strategyTasks] of profile.strategies) {
    const groupRuns = [...strategyTasks.values()].flat();
    const exactRuns = groupRuns.filter((run) => run.evaluation != null && Number.isFinite(run.evaluation.score));
    const criterionRuns = groupRuns.filter((run) => run.criterion_evaluation?.status === "complete");
    const criteriaPassed = criterionRuns.reduce((sum, run) => sum + (run.criterion_evaluation.passed_count || 0), 0);
    const criteriaTotal = criterionRuns.reduce((sum, run) => sum + (run.criterion_evaluation.criteria_count || 0), 0);
    const successfulTaskExactScores = [...strategyTasks.values()].map((items) => {
      const scores = items.filter((run) => Number.isFinite(run.evaluation?.score)).map((run) => run.evaluation.score);
      return scores.length ? scores.reduce((a,b) => a+b,0) / scores.length : null;
    }).filter(Number.isFinite);
    const successfulTaskCriterionScores = [...strategyTasks.values()].map((items) => {
      const evaluated = items.filter((run) => run.criterion_evaluation?.status === "complete");
      const total = evaluated.reduce((sum, run) => sum + (run.criterion_evaluation.criteria_count || 0), 0);
      const passed = evaluated.reduce((sum, run) => sum + (run.criterion_evaluation.passed_count || 0), 0);
      return total ? passed / total : null;
    }).filter(Number.isFinite);
    output.push({
      ...profile, strategy, taskCount:strategyTasks.size, runs:groupRuns,
      responses:groupRuns.filter((run) => run.response != null).length,
      errors:groupRuns.filter((run) => run.error || run.criterion_evaluation?.status === "error").length,
      exactRuns, exactPassed:exactRuns.filter((run) => run.evaluation.exact_match).length,
      exactTaskAverage:successfulTaskExactScores.length ? successfulTaskExactScores.reduce((a,b) => a+b,0) / successfulTaskExactScores.length : null,
      exactTaskCount:successfulTaskExactScores.length,
      criteriaPassed, criteriaTotal,
      criterionTaskAverage:successfulTaskCriterionScores.length ? successfulTaskCriterionScores.reduce((a,b) => a+b,0) / successfulTaskCriterionScores.length : null,
      criterionTaskCount:successfulTaskCriterionScores.length,
      medianContext:median(groupRuns.map((run) => run.metrics?.final_assembled_context_tokens)),
      medianCompression:median(groupRuns.map((run) => run.metrics?.compression_ratio)),
      medianRetrieved:median(groupRuns.map((run) => run.metrics?.addresses_retrieved)),
      medianExpansions:median(groupRuns.map((run) => run.metrics?.expansions)),
      medianRetrievalTime:median(groupRuns.map((run) => run.metrics?.retrieval_time_ms)),
      medianExpansionTime:median(groupRuns.map((run) => run.metrics?.expansion_time_ms)),
      medianModelTokens:median(groupRuns.map((run) => run.metrics?.total_model_tokens)),
      medianTime:median(groupRuns.map((run) => run.metrics?.total_execution_time_ms)),
    });
  }
  return output.sort((a,b) => a.category.localeCompare(b.category) || (a.budget ?? 0) - (b.budget ?? 0) || a.model.localeCompare(b.model) || a.strategy.localeCompare(b.strategy));
}
function groupCriterionResults(rows) {
  const groups = new Map();
  for (const run of rows) {
    if (run.criterion_evaluation?.status !== "complete") continue;
    for (const item of run.criterion_evaluation.criteria || []) {
      const key = JSON.stringify([run.category || "Uncategorized",run.context_budget ?? null,run.model || "Offline preparation",run.criterion_evaluation.model || run.evaluation_model || "Not recorded",run.strategy || "unknown",item.criterion]);
      if (!groups.has(key)) groups.set(key, {category:run.category || "Uncategorized",budget:run.context_budget ?? null,model:run.model || "Offline preparation",evaluator:run.criterion_evaluation.model || run.evaluation_model || "Not recorded",strategy:run.strategy || "unknown",criterion:item.criterion,passed:0,total:0,tasks:new Set()});
      const group = groups.get(key);
      group.total++;
      group.passed += item.passed ? 1 : 0;
      group.tasks.add(run.comparison_id || run.run_id);
    }
  }
  return [...groups.values()].sort((a,b) => a.category.localeCompare(b.category) || (a.budget ?? 0) - (b.budget ?? 0) || a.criterion.localeCompare(b.criterion) || a.strategy.localeCompare(b.strategy));
}
function groupLanguageComparisons(rows) {
  const groups = new Map();
  for (const run of rows) {
    const metric = run.language_metrics;
    if (!metric || metric.measurement_validity === "rejected") continue;
    const revision = metric.measurement_revision || run.measurement_revision || "legacy";
    const key = JSON.stringify([revision,metric.fixture_id,metric.language]);
    if (!groups.has(key)) groups.set(key, {revision,fixture:metric.fixture_id,language:metric.language,strategies:new Map()});
    const group = groups.get(key);
    const strategy = metric.strategy || "asm";
    if (!group.strategies.has(strategy)) group.strategies.set(strategy, []);
    group.strategies.get(strategy).push(run);
  }
  return [...groups.values()].map((group) => {
    const summarize = (items) => ({
      count:items.length,
      time:median(items.map((run) => run.language_metrics.execution_time_ms)),
      memory:median(items.map((run) => run.language_metrics.memory_bytes)),
      cpuCount:items.filter((run) => Number.isFinite(run.language_metrics.cpu_utilization_percent)).length,
    });
    const asm = summarize(group.strategies.get("asm") || []);
    const baseline = summarize(group.strategies.get("baseline") || []);
    const delta = Number.isFinite(asm.time) && Number.isFinite(baseline.time) && baseline.time !== 0
      ? (asm.time - baseline.time) * 100 / baseline.time : null;
    return {...group,asm,baseline,delta};
  }).sort((a,b) => a.revision.localeCompare(b.revision) || a.fixture.localeCompare(b.fixture) || a.language.localeCompare(b.language));
}
function renderResults() {
  const experimentRuns = runs.filter((run) => !run.language_metrics);
  const modelGroups = groupModelProfiles(experimentRuns);
  const asmRuns = experimentRuns.filter((run) => run.strategy === "asm");
  const withModel = experimentRuns.filter((run) => run.model_metrics);
  const criteriaEvaluated = experimentRuns.filter((run) => run.criterion_evaluation?.status === "complete");
  const cards = [
    ["Stored runs",runs.length], ["ASM runs",asmRuns.length],
    ["Runs with model response",withModel.length], ["Criterion evaluations",criteriaEvaluated.length],
    ["Runs with errors",runs.filter((run) => run.error || run.criterion_evaluation?.status === "error").length]
  ];
  $("#summary").innerHTML = cards.map(([label,value]) => `<div class="metric"><small>${esc(label)}</small><strong>${fmt(value,0)}</strong></div>`).join("");
  const profileLabel = (group) => `${fmt(group.budget,0)} · ${group.category} · ${group.model} · ${strategyName(group.strategy)} · n=${group.runs.length}`;
  renderBars("#token-chart", modelGroups, (group) => group.medianContext, profileLabel);
  renderBars("#time-chart", modelGroups, (group) => group.medianTime, profileLabel, "#e2a64b");
  renderBars("#quality-chart", modelGroups, (group) => group.exactTaskAverage == null ? null : group.exactTaskAverage * 100, profileLabel, "#769ee8");
  renderBars("#criterion-chart", modelGroups, (group) => group.criterionTaskAverage == null ? null : group.criterionTaskAverage * 100, profileLabel, "#ba88e8");
  renderBars("#compression-chart", modelGroups.filter((group) => group.strategy === "asm"), (group) => group.medianCompression, profileLabel, "#ba88e8");
  renderBars("#retrieval-chart", modelGroups.filter((group) => group.strategy === "asm"), (group) => group.medianRetrieved, profileLabel);
  renderBars("#expansion-chart", modelGroups.filter((group) => group.strategy === "asm"), (group) => group.medianExpansions, profileLabel, "#e2a64b");
  renderBars("#retrieval-time-chart", modelGroups.filter((group) => group.strategy === "asm"), (group) => group.medianRetrievalTime, profileLabel, "#769ee8");
  renderBars("#expansion-time-chart", modelGroups.filter((group) => group.strategy === "asm"), (group) => group.medianExpansionTime, profileLabel, "#e2a64b");
  renderQualityTokenChart(modelGroups);
  renderBars("#budget-chart", modelGroups, (group) => group.exactTaskAverage == null ? null : group.exactTaskAverage * 100, profileLabel, "#e2a64b");
  const languageRuns = runs.filter((run) => run.language_metrics && run.language_metrics.measurement_validity !== "rejected");
  const revisions = [...new Set(languageRuns.map((run) => run.language_metrics.measurement_revision || run.measurement_revision || "legacy"))].sort();
  const selectedRevision = $("#language-revision-filter").value;
  if (!selectedRevision || !revisions.includes(selectedRevision)) {
    $("#language-revision-filter").innerHTML = revisions.map((revision) => `<option value="${esc(revision)}">${esc(revisionName(revision))}</option>`).join("");
    $("#language-revision-filter").value = revisions.includes("asm-bench-v2.0") ? "asm-bench-v2.0" : revisions.at(-1) || "";
  }
  const revisionFilter = $("#language-revision-filter").value;
  const selectedLanguageRuns = languageRuns.filter((run) => (run.language_metrics.measurement_revision || run.measurement_revision || "legacy") === revisionFilter);
  const languageSummary = aggregateLanguageRuns(selectedLanguageRuns);
  const languageLabel = (run) => `${languageName(run.language_metrics?.language)} · ${strategyName(run.language_metrics?.strategy || "asm")} · ${fixtureName(run.language_metrics?.fixture_id)}`;
  renderBars("#language-chart", languageSummary, (run) => run.language_metrics?.execution_time_ms, (run) => `${languageLabel(run)} n=${run.language_metrics?.repetitions}`);
  renderBars("#memory-chart", languageSummary, (run) => run.language_metrics?.memory_bytes, (run) => `${languageLabel(run)} n=${run.language_metrics?.repetitions}`, "#769ee8");
  renderBars("#cpu-chart", languageSummary, (run) => run.language_metrics?.cpu_utilization_percent, (run) => `${languageLabel(run)} n=${run.language_metrics?.repetitions}`, "#ba88e8");
  renderBars("#parse-chart", languageSummary, (run) => run.language_metrics?.operation_times_ns?.input_parse_ns, languageLabel);
  renderBars("#retrieval-chart-language", languageSummary, (run) => run.language_metrics?.operation_times_ns?.retrieval_ns, languageLabel, "#e2a64b");
  renderBars("#lookup-chart", languageSummary, (run) => run.language_metrics?.operation_times_ns?.address_lookup_ns, languageLabel, "#769ee8");
  renderBars("#assembly-chart", languageSummary, (run) => run.language_metrics?.operation_times_ns?.expansion_assembly_ns, languageLabel, "#ba88e8");
  renderBars("#serialization-chart", languageSummary, (run) => run.language_metrics?.operation_times_ns?.serialization_ns, languageLabel, "#e2a64b");
  renderAggregates(runs);
  const comparisonLabels = new Map();
  for (const run of runs) if (run.comparison_id && !comparisonLabels.has(run.comparison_id)) comparisonLabels.set(run.comparison_id, "Comparison " + (comparisonLabels.size + 1));
  $("#results-body").innerHTML = runs.slice().reverse().map((run) => `<tr>
    <td><button data-run="${esc(run.run_id)}">${esc(run.run_id.slice(0,8))}</button></td><td>${esc(comparisonLabels.get(run.comparison_id) || "—")}</td><td>${esc(new Date(run.timestamp).toLocaleString())}</td>
    <td><span class="tag">${esc(run.language_metrics ? languageName(run.language_metrics.language) + " · " + strategyName(run.language_metrics.strategy || "asm") : strategyName(run.strategy))}</span></td><td>${fmt(run.context_budget,0)}</td><td>${esc(run.model || (run.language_metrics ? languageName(run.language_metrics.language) : "—"))}</td>
    <td>${fmt(run.metrics?.final_assembled_context_tokens ?? run.raw_output?.context_tokens,0)}</td><td>${run.criterion_evaluation?.status === "complete" ? `${fmt(run.criterion_evaluation.pass_percentage)}%` : "—"}</td><td>${fmt(run.metrics?.total_model_prompt_tokens,0)} / ${fmt(run.metrics?.total_model_completion_tokens,0)}</td><td>${esc(run.language_metrics?.measurement_validity === "rejected" ? "Excluded from analysis: " + (run.language_metrics.validity_note || "measurement rejected") : run.criterion_evaluation?.error || run.error || "No recorded errors")}</td></tr>`).join("") || `<tr><td colspan="10">No runs stored yet.</td></tr>`;
  document.querySelectorAll("[data-run]").forEach((button) => button.addEventListener("click", () => inspectRun(button.dataset.run)));
}
function inspectRun(id) {
  const run = runs.find((item) => item.run_id === id);
  if (!run) return;
  $("#inspector").classList.remove("hidden");
  $("#inspect-detail").innerHTML = `<dl class="detail-grid"><dt>Run ID</dt><dd>${esc(run.run_id)}</dd><dt>Comparison</dt><dd>${esc(run.comparison_id ? "Comparison " + ([...new Set(runs.filter((item) => item.comparison_id).map((item) => item.comparison_id))].indexOf(run.comparison_id) + 1) : "Individual run")}</dd><dt>Comparison repeat/order</dt><dd>${esc(run.comparison_repeat || "—")} · ${esc((run.comparison_order || []).map(strategyName).join(" then ") || "—")}</dd><dt>Input/settings signature</dt><dd>${esc(run.input_signature || "—")}</dd><dt>Language benchmark measurements</dt><dd>${readableValue(run.language_metrics)}</dd><dt>Model response</dt><dd>${run.response ? `<pre>${esc(run.response)}</pre>` : "No model response stored."}</dd><dt>Normalized exact-match evaluation</dt><dd>${readableValue(run.evaluation)}</dd><dt>Criterion pass/fail evaluation</dt><dd>${readableValue(run.criterion_evaluation)}</dd><dt>Experiment measurements</dt><dd>${readableValue(run.metrics)}</dd><dt>Answer model usage</dt><dd>${readableValue(run.model_metrics)}</dd><dt>Compression model usage</dt><dd>${readableValue(run.compression_model_metrics)}</dd><dt>Criterion evaluator usage</dt><dd>${readableValue(run.criterion_evaluation_model_metrics)}</dd><dt>Source</dt><dd><pre>${esc(run.source || "—")}</pre></dd><dt>Compressed representation</dt><dd>${readableValue(run.provenance?.representations || [])}</dd><dt>Retrieved/expanded context</dt><dd>${readableValue(run.context?.selected || run.raw_output || [])}</dd><dt>Final answer prompt</dt><dd><pre>${esc(run.prompt || "—")}</pre></dd><dt>Error</dt><dd>${esc(run.error || run.criterion_evaluation?.error || "—")}</dd></dl>`;
  $("#inspector").scrollIntoView({behavior:"smooth",block:"start"});
}

function download(name, type, content) {
  const blob = new Blob([content], {type}); const url = URL.createObjectURL(blob); const link = document.createElement("a");
  link.href = url; link.download = name; link.click(); URL.revokeObjectURL(url);
}
$("#export-json").addEventListener("click", () => download("asm-results.json","application/json",JSON.stringify(runs,null,2)));
function renderImradReport() {
  const experiments = runs.filter((run) => !run.language_metrics);
  const allLanguageRuns = runs.filter((run) => run.language_metrics);
  const languageRuns = allLanguageRuns.filter((run) => run.language_metrics.measurement_validity !== "rejected");
  const excludedLanguageRuns = allLanguageRuns.length - languageRuns.length;
  const comparisons = new Map();
  for (const run of experiments) {
    const comparisonId = run.comparison_id || ("run:" + run.run_id);
    const key = comparisonId + "|" + (run.strategy || "unknown");
    if (!comparisons.has(key)) comparisons.set(key, {comparisonId, strategy:run.strategy || "unknown", runs:[]});
    comparisons.get(key).runs.push(run);
  }
  const comparisonLabels = new Map();
  let comparisonIndex = 0;
  for (const group of comparisons.values()) if (!group.comparisonId.startsWith("run:") && !comparisonLabels.has(group.comparisonId)) comparisonLabels.set(group.comparisonId, "Comparison " + (++comparisonIndex));
  const comparisonRows = [...comparisons.values()].map((group) => {
    const context = median(group.runs.map((run) => run.metrics?.final_assembled_context_tokens));
    const score = median(group.runs.map((run) => run.evaluation?.score));
    const criterionScore = median(group.runs.map((run) => run.criterion_evaluation?.status === "complete" ? run.criterion_evaluation.pass_percentage : null));
    const label = group.comparisonId.startsWith("run:") ? "Individual run" : comparisonLabels.get(group.comparisonId);
    return "<tr><td>" + esc(label) + "</td><td>" + esc(strategyName(group.strategy)) + "</td><td>" + group.runs.length + "</td><td>" + fmt(context, 0) + "</td><td>" + fmt(score) + "</td><td>" + (criterionScore == null ? "Not scored" : fmt(criterionScore) + "%") + "</td><td>" + group.runs.filter((run) => run.error || run.criterion_evaluation?.status === "error").length + "</td></tr>";
  }).join("");
  const criterionEvaluations = experiments.filter((run) => run.criterion_evaluation?.status === "complete");
  const criterionTotal = criterionEvaluations.reduce((sum, run) => sum + (run.criterion_evaluation.criteria_count || 0), 0);
  const criterionPassed = criterionEvaluations.reduce((sum, run) => sum + (run.criterion_evaluation.passed_count || 0), 0);
  const criterionPercentage = criterionTotal ? criterionPassed * 100 / criterionTotal : null;
  const comparisonForRun = (run) => run.comparison_id ? comparisonLabels.get(run.comparison_id) : "Individual run";
  const criterionRows = criterionEvaluations.flatMap((run) => (run.criterion_evaluation.criteria || []).map((item) =>
    "<tr><td>" + esc(comparisonForRun(run)) + "</td><td>" + esc(run.comparison_repeat || "Individual") + "</td><td>" + esc(strategyName(run.strategy)) + "</td><td>" + esc(item.criterion) + "</td><td>" + (item.passed ? "Passed" : "Failed") + "</td><td>" + esc(item.rationale) + "</td><td>" + esc(run.criterion_evaluation.model || "Not recorded") + "</td></tr>"
  )).join("");
  const languageRows = aggregateLanguageRuns(languageRuns).map((run) => {
    const metric = run.language_metrics;
    return "<tr><td>" + esc(languageName(metric.language)) + "</td><td>" + esc(strategyName(metric.strategy || "asm")) + "</td><td>" + esc(fixtureName(metric.fixture_id)) + "</td><td>" + esc(revisionName(metric.measurement_revision)) + "</td><td>" + metric.repetitions + "</td><td>" + fmt(metric.execution_time_ms, 4) + "</td><td>" + fmt(metric.memory_bytes, 0) + "</td></tr>";
  }).join("");
  const modelNames = [...new Set(experiments.map((run) => run.model).filter(Boolean))];
  const correct = experiments.filter((run) => run.evaluation?.exact_match === true).length;
  const scored = experiments.filter((run) => run.evaluation != null).length;
  const modelNamesForEval = [...new Set(criterionEvaluations.map((run) => run.criterion_evaluation.model).filter(Boolean))];
  const strategyCounts = ["asm", "baseline"].map((strategy) => strategyName(strategy) + ": " + experiments.filter((run) => run.strategy === strategy).length).join("; ");
  const comparisonGroups = new Map();
  for (const run of experiments) if (run.comparison_id) {
    if (!comparisonGroups.has(run.comparison_id)) comparisonGroups.set(run.comparison_id, new Set());
    comparisonGroups.get(run.comparison_id).add(run.strategy);
  }
  const matchedComparisons = [...comparisonGroups.values()].filter((strategies) => strategies.has("asm") && strategies.has("baseline")).length;
  const languageStrategies = [...new Set(languageRuns.map((run) => run.language_metrics?.strategy || "asm"))].map(strategyName).join(", ") || "none";
  const exclusionNotes = [...new Set(allLanguageRuns.filter((run) => run.language_metrics.measurement_validity === "rejected").map((run) => run.language_metrics.validity_note).filter(Boolean))];
  const discussion = experiments.length || languageRuns.length
    ? matchedComparisons + " paired ASM/baseline experiment comparison(s) are present. Answer scoring is normalized exact match only; it does not measure general semantic equivalence. " + languageRuns.length + " accepted language measurements cover the recorded strategies. " + excludedLanguageRuns + " measurement(s) marked rejected are excluded from summary tables. " + exclusionNotes.join(" ") + " These timings describe the listed fixtures and toolchains, not a universal performance winner. Interpret token and runtime results with correctness, source traceability, repetition counts, and measurement revisions. Small samples and short fixtures limit generalization."
    : "No saved experiment or language benchmark data is available, so no empirical conclusion can be drawn.";
  const findings = [
    scored ? correct + " of " + scored + " exact-match evaluation(s) passed." : "No exact-match evaluations are available.",
    criterionTotal ? criterionPassed + " of " + criterionTotal + " criteria passed (" + fmt(criterionPercentage) + "%) across " + criterionEvaluations.length + " answer(s), judged by " + (modelNamesForEval.join(", ") || "a local model") + "." : "No completed criterion evaluations are available.",
    matchedComparisons + " paired ASM/baseline model comparison(s) and " + languageRuns.length + " accepted language run(s) are stored."
  ];
  const conclusion = criterionTotal || scored
    ? "The stored results provide a measured comparison for the tested inputs. Exact-match results are deterministic string comparisons; criterion percentages are local-model judgments against the supplied criteria and are not a gold-standard accuracy measure. Interpret them with the individual rationales, source material, and comparison controls."
    : "There are not enough scored model results to draw a conclusion. Add expected answers or evaluation criteria, enable local inference, and rerun paired comparisons.";
  $("#imrad-report").innerHTML = [
    "<header><p class='eyebrow'>ASM LOCAL RESEARCH</p><h1>Benchmark Summary</h1><p>IMRAD report · generated ", esc(new Date().toLocaleDateString()), "</p></header>",
    "<section class='findings-summary'><h2>Findings Summary</h2><ul>", findings.map((item) => "<li>" + esc(item) + "</li>").join(""), "</ul></section>",
    "<section><h2>Introduction</h2><p>This report summarizes stored measurements from the Addressable Semantic Memory (ASM) prototype. The project evaluates whether retrieving addressable source information can preserve answer quality while changing context use and execution cost. It includes paired model experiments with ASM and baseline strategies, plus three-language operation benchmarks.</p><p><strong>Included data:</strong> ", experiments.length, " model experiment run(s), ", matchedComparisons, " paired comparison(s), and ", languageRuns.length, " accepted language benchmark run(s). Model(s): ", esc(modelNames.join(", ") || "not recorded"), ".</p></section>",
    "<section><h2>Methods</h2><p>Model experiments compare stored baseline and ASM runs under recorded source, question, context-budget, model, model-version, expansion, and generation settings. Baseline context takes the original source prefix up to its token budget; ASM retrieves relevant addressable fragments and assembles evidence within the same budget. Normalized exact match is recorded separately from an optional second inference pass that judges each supplied criterion using the original source, question, and generated answer. The evaluator can use the answer model or a separately selected local model. Its criterion percentage is passed criteria divided by all criteria scored.</p><p>Language benchmarks run equivalent fixtures through C, Go, and Rust. The ASM path performs retrieval, lookup, and expansion. The no-ASM baseline directly truncates original fixture text in input order to the same evidence-token budget. Runs are correctness-gated and report warmups, repetitions, operation times, toolchain settings, and available process metrics. Language strategies recorded: ", esc(languageStrategies), ". Model strategy counts: ", esc(strategyCounts), ".</p></section>",
    "<section class='results-section'><h2>Results</h2><h3>Model experiments</h3><p>", scored ? correct + " of " + scored + " scored run(s) matched the expected answer exactly." : "No model runs have exact-match scores.", " Criterion evaluation: ", criterionTotal ? criterionPassed + " of " + criterionTotal + " passed (" + fmt(criterionPercentage) + "%)." : "No completed criterion evaluation.", "</p><table><thead><tr><th>Comparison</th><th>Strategy</th><th>Runs</th><th>Median context tokens</th><th>Median exact match</th><th>Median criterion pass rate</th><th>Errors</th></tr></thead><tbody>", comparisonRows || "<tr><td colspan='7'>No model experiment data.</td></tr>", "</tbody></table><h3>Criterion-level judgments</h3><table class='criteria-table'><thead><tr><th>Comparison</th><th>Repeat</th><th>Strategy</th><th>Criterion</th><th>Result</th><th>Evaluator rationale</th><th>Evaluator model</th></tr></thead><tbody>", criterionRows || "<tr><td colspan='7'>No completed criterion evaluations.</td></tr>", "</tbody></table><h3>Language benchmark medians</h3><table><thead><tr><th>Language</th><th>Strategy</th><th>Fixture</th><th>Revision</th><th>Runs</th><th>Median runtime (ms)</th><th>Peak memory (bytes)</th></tr></thead><tbody>", languageRows || "<tr><td colspan='7'>No language benchmark data.</td></tr>", "</tbody></table></section>",
    "<section><h2>Discussion</h2><p>", esc(discussion), "</p><p>Missing resource measurements are shown as unavailable. This summary aggregates only stored records and does not infer unmeasured values.</p></section>",
    "<section class='conclusion'><h2>Conclusion</h2><p>", esc(conclusion), "</p></section>",
    "<footer>ASM local benchmark · generated from saved results · ", runs.length, " total stored record(s)</footer>"
  ].join("");
}
$("#export-pdf").addEventListener("click", () => {
  renderImradReport();
  document.body.classList.add("print-report");
  window.print();
  document.body.classList.remove("print-report");
});
$("#export-csv").addEventListener("click", () => {
  const fields = ["run_id","comparison_id","comparison_repeat","input_signature","timestamp","strategy","compression_mode","category","context_budget","model","model_version","evaluation_model","evaluation_model_version","original_source_tokens","compressed_representation_tokens","compression_ratio","final_assembled_context_tokens","question_tokens","system_instruction_tokens","source_fragmentation_time_ms","representation_indexing_time_ms","retrieval_time_ms","expansion_time_ms","context_assembly_time_ms","semantic_compression_model_time_ns","total_execution_time_ms","total_model_prompt_tokens","total_model_completion_tokens","exact_match_score","criterion_pass_percentage","criterion_status","criteria_passed","criteria_count","criterion_evaluation_time_ms","criterion_evaluator_prompt_tokens","criterion_evaluator_completion_tokens","language","language_strategy","fixture_id","measurement_revision","measurement_validity","measurement_note","language_repetitions","language_execution_time_ns","language_input_parse_ns","language_retrieval_ns","language_address_lookup_ns","language_expansion_assembly_ns","language_serialization_ns","process_wall_time_ns","memory_bytes","cpu_utilization_percent","throughput_tokens_per_second","output_size_bytes","compile_time_ns","toolchain_version","response","error"];
  const quote = (value) => `"${String(value ?? "").replaceAll('"','""')}"`;
  const comparisonNumbers = new Map([...new Set(runs.map((run) => run.comparison_id).filter(Boolean))].map((id, index) => [id, "Comparison " + (index + 1)]));
  const lines = [fields.map((field) => quote(fieldName(field))).join(","),...runs.map((run) => {
    const values = [run.run_id,run.comparison_id,run.comparison_repeat,run.input_signature,run.timestamp,run.strategy,run.compression_mode,run.category,run.context_budget,run.model,run.model_version,run.evaluation_model,run.evaluation_model_version,run.metrics?.original_source_tokens,run.metrics?.compressed_representation_tokens,run.metrics?.compression_ratio,run.metrics?.final_assembled_context_tokens,run.metrics?.question_tokens,run.metrics?.system_instruction_tokens,run.metrics?.source_fragmentation_time_ms,run.metrics?.representation_indexing_time_ms,run.metrics?.retrieval_time_ms,run.metrics?.expansion_time_ms,run.metrics?.context_assembly_time_ms,run.metrics?.semantic_compression_model_time_ns,run.metrics?.total_execution_time_ms,run.metrics?.total_model_prompt_tokens,run.metrics?.total_model_completion_tokens,run.evaluation?.score,run.criterion_evaluation?.pass_percentage,run.criterion_evaluation?.status,run.criterion_evaluation?.passed_count,run.criterion_evaluation?.criteria_count,run.metrics?.criterion_evaluation_time_ms,run.criterion_evaluation_model_metrics?.prompt_tokens,run.criterion_evaluation_model_metrics?.completion_tokens,run.language_metrics?.language,run.language_metrics?.strategy,run.language_metrics?.fixture_id,run.language_metrics?.measurement_revision,run.language_metrics?.measurement_validity,run.language_metrics?.validity_note,run.language_metrics?.repetitions,run.language_metrics?.execution_time_ns,run.language_metrics?.operation_times_ns?.input_parse_ns,run.language_metrics?.operation_times_ns?.retrieval_ns,run.language_metrics?.operation_times_ns?.address_lookup_ns,run.language_metrics?.operation_times_ns?.expansion_assembly_ns,run.language_metrics?.operation_times_ns?.serialization_ns,run.language_metrics?.process_wall_time_ns,run.language_metrics?.memory_bytes,run.language_metrics?.cpu_utilization_percent,run.language_metrics?.throughput_tokens_per_second,run.language_metrics?.output_size_bytes,run.language_metrics?.compile_time_ns,run.language_metrics?.toolchain_version,run.response,run.error];
    values[5] = run.strategy ? strategyName(run.strategy) : "";
    values[1] = run.comparison_id ? comparisonNumbers.get(run.comparison_id) : "Individual run";
    values[36] = run.language_metrics ? languageName(run.language_metrics.language) : "";
    values[37] = run.language_metrics ? strategyName(run.language_metrics.strategy || "asm") : "";
    values[38] = run.language_metrics ? fixtureName(run.language_metrics.fixture_id) : "";
    values[39] = run.language_metrics ? revisionName(run.language_metrics.measurement_revision || run.measurement_revision) : "";
    return values.map(quote).join(",");
  })];
  download("asm-results.csv","text/csv",lines.join("\r\n"));
});
init(); loadResults(); loadSystemEvents();

// -- System health and automatic alerts (local system-event log) --------------

async function loadSystemEvents() {
  try {
    const health = await api("/api/system-events");
    renderSystemHealth(health);
  } catch (error) {
    $("#system-active-alert-count").textContent = "–";
    $("#system-error-count").textContent = "–";
    $("#system-malformed-count").textContent = "–";
    $("#system-alert-list").innerHTML = "";
    $("#system-event-list").innerHTML = `<div class="event-row severity-error"><p class="event-message">Could not read the system event log: ${esc(error.message)}</p></div>`;
  }
}

function systemSeverityCount(counts) {
  return Number(counts.error || 0) + Number(counts.critical || 0);
}

function renderSystemHealth(health) {
  const counts = health.counts || {};
  const activeAlerts = health.active_alerts || [];
  const malformed = health.malformed_lines || [];
  $("#system-active-alert-count").textContent = String(activeAlerts.length);
  $("#system-error-count").textContent = String(systemSeverityCount(counts));
  $("#system-malformed-count").textContent = String(malformed.length);
  $("#system-alert-list").innerHTML = activeAlerts.length
    ? activeAlerts.map(systemEventRow).join("")
    : `<p class="event-empty">No alerts in the last ${health.alert_window_minutes ?? 60} minutes; all monitored components are reporting normally.</p>`;
  $("#system-event-list").innerHTML = (health.events || []).length
    ? health.events.map(systemEventRow).join("")
    : '<p class="event-empty">No system events recorded yet.</p>';
}

function systemEventRow(event) {
  const severity = event.severity || "info";
  const stamp = event.timestamp ? new Date(event.timestamp).toLocaleString() : "unknown time";
  const detailEntries = Object.entries(event.details || {});
  const detailsBlock = detailEntries.length
    ? `<details class="event-details"><summary>Details</summary><dl class="detail-grid"><dt>Event ID</dt><dd>${esc(event.event_id || "")}</dd>${detailEntries.map(([key, value]) => `<dt>${esc(key)}</dt><dd>${esc(String(value))}</dd>`).join("")}</dl></details>`
    : `<details class="event-details"><summary>Details</summary><dl class="detail-grid"><dt>Event ID</dt><dd>${esc(event.event_id || "")}</dd></dl></details>`;
  return `<details class="event-row severity-${esc(severity)}">
    <summary>
      <span class="tag severity-${esc(severity)}">${esc(severity.toUpperCase())}</span>
      ${event.alert_type ? `<span class="tag severity-critical">Escalation · ${esc(event.alert_type)}</span>` : ""}
      <span class="event-source">${esc(event.component || "system")} / ${esc(event.event_type || "event")}</span>
      <span class="event-time">${esc(stamp)}</span>
    </summary>
    <p class="event-message">${esc(event.message || "")}</p>
    ${detailsBlock}
  </details>`;
}
