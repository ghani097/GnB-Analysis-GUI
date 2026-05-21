function gnb_gui_runner(rawFolder, outFolder, heightsFile)
%GNB_GUI_RUNNER  Custom Walking + Static pipeline for any data folder.
%
%  Classifies each CSV as 'walking' or 'static' using filename keywords
%  and a row-count fallback, then routes each through the appropriate
%  SincMotion function (unchanged existing functions on MATLAB path).
%
%  Arguments:
%    rawFolder   - folder containing mixed walking + static CSV files
%    outFolder   - destination folder
%    heightsFile - path to XLSX/CSV with heights (ID/Name + Height_m or _cm)
%
%  Outputs:
%    outFolder/custom_gait_outcomes.xlsx    (walking files)
%    outFolder/custom_static_outcomes.xlsx  (static files)

if ~exist(outFolder, 'dir'), mkdir(outFolder); end

heightLookup = buildHeightLookup(heightsFile);
files = dir(fullfile(rawFolder, '*.csv'));
fprintf('Found %d CSV files in: %s\n', numel(files), rawFolder);

gaitHeaders   = {'File','Participant','WalkingBalance_pct',...
    'StepLength_m','StepLength_Left_m','StepLength_Right_m',...
    'StepTime_s','StepTime_Left_s','StepTime_Right_s',...
    'StepLength_Variability_pct','StepTime_Variability_pct',...
    'StepLength_Asymmetry_pct','StepTime_Asymmetry_pct',...
    'WalkingSpeed_m_s','StepCount_Lap1','StepCount_Lap2',...
    'StepCount_Lap3','StepCount_Lap4'};
staticHeaders = {'File','Participant','Stability','Stability_ML','Stability_AP'};

gaitRows   = {};
staticRows = {};
nOK = 0; nErr = 0;

for i = 1:numel(files)
    fname  = files(i).name;
    fpath  = fullfile(rawFolder, fname);
    [stem, ~] = fileparts(fname);
    kind   = classifyFile(stem, fpath);
    fprintf('  [%-7s] %s\n', kind, fname);

    participantLabel = stem;  % filename stem used as participant identifier
    heightM = lookupHeightByName(heightLookup, stem);

    try
        if strcmp(kind, 'walking')
            [accelData, rotData, timeVect, gyroData] = ...
                loadSumeetaFile(100, fpath);
            outcomes = estimateGnBGaitOutcomes(timeVect, accelData, rotData, ...
                           gyroData, 100, heightM, 0, 0);
            gaitRows{end+1} = [{fname}, {participantLabel}, ...
                                num2cell(outcomes(1:16))]; %#ok<AGROW>

        elseif strcmp(kind, 'static')
            [accelData, rotData, ~, ~] = loadGnBExportedFile(100, fpath);
            outcomes = estimateGnBStaticOutcomes(accelData, rotData, 100, 0);
            staticRows{end+1} = [{fname}, {participantLabel}, ...
                                  num2cell(outcomes(1:3))}]; %#ok<AGROW>
        else
            fprintf('  SKIP (unknown type): %s\n', fname);
            continue;
        end
        nOK = nOK + 1;
    catch ME
        nErr = nErr + 1;
        fprintf('  ERR %s -> %s\n', fname, ME.message);
    end
end

fprintf('\nDone: %d OK, %d errors\n', nOK, nErr);

%% Write outputs

if ~isempty(gaitRows)
    outGait = fullfile(outFolder, 'custom_gait_outcomes.xlsx');
    writecell([gaitHeaders; vertcat(gaitRows{:})], outGait);
    fprintf('Saved gait outcomes:   %s\n', outGait);
else
    fprintf('No gait outcomes to write.\n');
end

if ~isempty(staticRows)
    outStatic = fullfile(outFolder, 'custom_static_outcomes.xlsx');
    writecell([staticHeaders; vertcat(staticRows{:})], outStatic);
    fprintf('Saved static outcomes: %s\n', outStatic);
else
    fprintf('No static outcomes to write.\n');
end
end

%% ─── Classification ────────────────────────────────────────────────────────

function kind = classifyFile(stem, fpath)
%CLASSIFYFILE  Returns 'walking', 'static', or 'unknown'.
    s = lower(strtrim(stem));

    % Static keywords
    staticKW = {'firm eo','firm ec','compliant eo','compliant ec',...
                'firm_eo','firm_ec','compliant_eo','compliant_ec',...
                ' eo',' ec','static','standing'};
    for k = 1:numel(staticKW)
        if contains(s, staticKW{k}), kind = 'static'; return; end
    end

    % Walking keywords
    walkKW = {'walk hf','walk ht','walk_hf','walk_ht','walking','gait'};
    for k = 1:numel(walkKW)
        if contains(s, walkKW{k}), kind = 'walking'; return; end
    end

    % Sumeeta filename pattern: p<N> <cond> <trial>
    if ~isempty(regexpi(s, ...
            '^(?:p|pl)\s*\d+\s*[,\s]+(?:bl|b|st|cb|pl)\s*\d+\s*$'))
        kind = 'walking'; return;
    end

    % Row-count fallback (threshold = 4000 rows at 100 Hz ≈ 40 s)
    kind = rowCountClassify(fpath);
end

function kind = rowCountClassify(fpath)
    try
        fid = fopen(fpath, 'rb');
        nLines = 0;
        while ~feof(fid)
            line = fgetl(fid);
            if ischar(line), nLines = nLines + 1; end
        end
        fclose(fid);
        nRows = max(0, nLines - 1);
        if     nRows >= 4000, kind = 'walking';
        elseif nRows >  0,    kind = 'static';
        else,                 kind = 'unknown';
        end
    catch
        kind = 'unknown';
    end
end

%% ─── Height lookup ─────────────────────────────────────────────────────────

function lookup = buildHeightLookup(heightsFile)
%  Returns a Map: string-key (lowercase name or numeric-string id) → double height_m
    lookup = containers.Map('KeyType','char','ValueType','double');
    if isempty(heightsFile) || ~exist(heightsFile, 'file'), return; end
    T = readtable(heightsFile, 'VariableNamingRule', 'preserve');
    normNames = lower(regexprep(string(T.Properties.VariableNames), '[^a-z0-9]+', '_'));

    % Accept 'name', 'id', or first column as participant identifier
    nameIdx = find(strcmp(normNames,'name') | strcmp(normNames,'id'), 1);
    if isempty(nameIdx), nameIdx = 1; end

    hmIdx  = find(strcmp(normNames,'height_m')  | strcmp(normNames,'height_m_'),  1);
    hcmIdx = find(strcmp(normNames,'height_cm') | strcmp(normNames,'height_cm_'), 1);
    if isempty(hmIdx) && isempty(hcmIdx), return; end

    for i = 1:height(T)
        raw_id = T{i, nameIdx};
        if iscell(raw_id), raw_id = raw_id{1}; end
        key = lower(strtrim(string(raw_id)));
        if strlength(key) == 0, continue; end

        if ~isempty(hmIdx)
            h = T{i, hmIdx};
        else
            h = T{i, hcmIdx} / 100;
        end
        if isnumeric(h) && ~isnan(h)
            lookup(key) = h;
        end
    end
    fprintf('Loaded heights for %d participants\n', lookup.Count);
end

function h = lookupHeightByName(lookup, stem)
    DEFAULT_H = 1.68;
    % Try full stem (lowercased), then extract leading numeric ID if present
    key = lower(strtrim(stem));
    if isKey(lookup, key)
        h = lookup(key); return;
    end
    % Try numeric ID from Sumeeta-style filenames: p<N> → key = "<N>"
    tok = regexp(key, '^(?:p|pl)\s*(\d+)', 'tokens', 'once');
    if ~isempty(tok)
        numKey = strtrim(tok{1});
        if isKey(lookup, numKey)
            h = lookup(numKey); return;
        end
    end
    h = DEFAULT_H;
end
