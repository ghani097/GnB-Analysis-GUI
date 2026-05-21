function gnb_custom_walker(rawFolder, outFolder, heightsFile)
%GNB_CUSTOM_WALKER  Custom walking-only pipeline for any data folder.
%
%  Accepts path arguments so the GUI can point it at any folder.
%  Replicates the logic of run_sumeeta_pipeline.m but without hardcoded paths.
%  Calls loadSumeetaFile and estimateGnBGaitOutcomes (both on MATLAB path).
%
%  Arguments:
%    rawFolder   - folder containing raw walking CSV files
%    outFolder   - destination folder for output Excel file
%    heightsFile - path to XLSX/CSV with heights
%                  (columns: ID (numeric) or Name + Height_m or Height_cm)
%
%  Output:
%    outFolder/custom_gait_outcomes.xlsx  — 19-column gait parameters

if ~exist(outFolder, 'dir'), mkdir(outFolder); end

heightLookup = buildHeightLookup(heightsFile);

%% Scan and parse CSV files (two-pass deduplication)

files = dir(fullfile(rawFolder, '*.csv'));
fprintf('Found %d CSV files in: %s\n', numel(files), rawFolder);

seenKeys = containers.Map('KeyType','char','ValueType','char');
parsed   = {};

% Pass 1: base files (no trailing "(N)" marker)
for i = 1:numel(files)
    fname = files(i).name;
    if ~isempty(regexp(fname, '\(\d+\)\.csv$', 'once')), continue; end
    meta = parseFilename(fname);
    if isempty(meta)
        fprintf('  Skip (unrecognized): %s\n', fname);
        continue;
    end
    key = makeKey(meta);
    if ~isKey(seenKeys, key)
        seenKeys(key) = fname;
        parsed{end+1} = struct('file', fname, 'meta', meta); %#ok<AGROW>
    end
end

% Pass 2: "(N)" duplicates — only add if key not yet seen
for i = 1:numel(files)
    fname = files(i).name;
    if isempty(regexp(fname, '\(\d+\)\.csv$', 'once')), continue; end
    meta = parseFilename(fname);
    if isempty(meta), continue; end
    key = makeKey(meta);
    if ~isKey(seenKeys, key)
        seenKeys(key) = fname;
        parsed{end+1} = struct('file', fname, 'meta', meta); %#ok<AGROW>
    else
        fprintf('  Skip duplicate: %s (base: %s)\n', fname, seenKeys(key));
    end
end

fprintf('Processing %d unique trial files\n\n', numel(parsed));

%% Extract gait parameters

headers = {'Participant_ID','Condition','Trial',...
    'WalkingBalance_pct',...
    'StepLength_m','StepLength_Left_m','StepLength_Right_m',...
    'StepTime_s','StepTime_Left_s','StepTime_Right_s',...
    'StepLength_Variability_pct','StepTime_Variability_pct',...
    'StepLength_Asymmetry_pct','StepTime_Asymmetry_pct',...
    'WalkingSpeed_m_s',...
    'StepCount_Lap1','StepCount_Lap2','StepCount_Lap3','StepCount_Lap4'};

outRows = {};
nOK = 0; nErr = 0;

for i = 1:numel(parsed)
    fname   = parsed{i}.file;
    meta    = parsed{i}.meta;
    fpath   = fullfile(rawFolder, fname);
    heightM = lookupHeight(heightLookup, meta.pid);

    try
        [accelData, rotData, timeVect, gyroData] = loadSumeetaFile(100, fpath);
        outcomes = estimateGnBGaitOutcomes(timeVect, accelData, rotData, ...
                       gyroData, 100, heightM, 0, 0);
        outRows{end+1} = [{meta.pid}, {meta.condition}, {meta.trial}, ...
                           num2cell(outcomes(1:16))]; %#ok<AGROW>
        nOK  = nOK + 1;
        fprintf('  OK  p%02d  %-20s  trial %d\n', meta.pid, meta.condition, meta.trial);
    catch ME
        nErr = nErr + 1;
        fprintf('  ERR p%02d  %-20s  trial %d  ->  %s\n', ...
            meta.pid, meta.condition, meta.trial, ME.message);
    end
end

fprintf('\nDone: %d OK, %d errors\n', nOK, nErr);

%% Sort and write output

outRows  = sortOutputRows(outRows);
outFile  = fullfile(outFolder, 'custom_gait_outcomes.xlsx');
save(fullfile(outFolder, 'custom_gait_checkpoint.mat'), 'headers', 'outRows');

if isempty(outRows)
    writecell(headers, outFile);
else
    writecell([headers; vertcat(outRows{:})], outFile);
end
fprintf('Saved: %s\n', outFile);
end

%% ─── Helpers ──────────────────────────────────────────────────────────────

function meta = parseFilename(fname)
    meta = [];
    [~, base, ext] = fileparts(fname);
    if ~strcmpi(ext, '.csv'), return; end
    base = regexprep(base, '\s*\(\d+\)\s*$', '');
    tokens = regexpi(base, ...
        '^(?:p|pl)\s*(\d+)\s*[,\s]+([a-z]+)\s*(\d+)\s*$', ...
        'tokens', 'ignorecase');
    if isempty(tokens), return; end
    t     = tokens{1};
    pid   = str2double(t{1});
    cond  = normalizeCondition(t{2});
    trial = str2double(t{3});
    if isempty(cond) || isnan(pid) || isnan(trial), return; end
    meta = struct('pid', pid, 'condition', cond, 'trial', trial);
end

function cond = normalizeCondition(raw)
    switch lower(strtrim(raw))
        case {'b','bl'},  cond = 'Baseline';
        case 'st',        cond = 'Stroop';
        case 'cb',        cond = 'CountingBackward';
        case 'pl',        cond = 'PhysicalLoad';
        otherwise,        cond = '';
    end
end

function k = makeKey(meta)
    k = sprintf('p%d_%s_%d', meta.pid, meta.condition, meta.trial);
end

function lookup = buildHeightLookup(heightsFile)
    lookup = containers.Map('KeyType','double','ValueType','double');
    if isempty(heightsFile) || ~exist(heightsFile, 'file'), return; end
    T = readtable(heightsFile, 'VariableNamingRule', 'preserve');
    normNames = lower(regexprep(string(T.Properties.VariableNames), '[^a-z0-9]+', '_'));

    idIdx  = find(strcmp(normNames,'id'),   1);
    hmIdx  = find(strcmp(normNames,'height_m') | strcmp(normNames,'height_m_'), 1);
    hcmIdx = find(strcmp(normNames,'height_cm')| strcmp(normNames,'height_cm_'), 1);

    if isempty(idIdx) || (isempty(hmIdx) && isempty(hcmIdx)), return; end

    for i = 1:height(T)
        pid = T{i, idIdx};
        if iscell(pid), pid = pid{1}; end
        pid = double(pid);
        if isnan(pid), continue; end
        if ~isempty(hmIdx)
            h = T{i, hmIdx};
        else
            h = T{i, hcmIdx} / 100;
        end
        if isnumeric(h) && ~isnan(h)
            lookup(pid) = h;
        end
    end
    fprintf('Loaded heights for %d participants\n', lookup.Count);
end

function h = lookupHeight(lookup, pid)
    DEFAULT_H = 1.68;
    if isKey(lookup, pid)
        h = lookup(pid);
    else
        h = DEFAULT_H;
        fprintf('    [WARN] No height for p%d, using %.2f m\n', pid, DEFAULT_H);
    end
end

function sorted = sortOutputRows(rows)
    condOrder = {'Baseline','Stroop','CountingBackward','PhysicalLoad'};
    n = numel(rows);
    if n == 0, sorted = rows; return; end
    keys = zeros(n, 3);
    for i = 1:n
        ci = find(strcmp(condOrder, rows{i}{2}));
        if isempty(ci), ci = 99; end
        keys(i,:) = [rows{i}{1}, ci, rows{i}{3}];
    end
    [~, ix] = sortrows(keys);
    sorted = rows(ix);
end
