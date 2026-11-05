## Task A5 - Design an AI application for citizen complaints (4 marks)

### A5.1 Sentiment and extractive summary
The sentiment baseline tokenises lowercase words and assigns +1 to good, clean, fast, helpful and improved; -1 to bad, dirty, slow, rude, smoke and broken. A directly preceding not, never or no flips the word's sign. Positive totals give positive, negative totals negative, and zero neutral. The practical function keeps sentence boundaries, so a negator cannot cross a sentence; the separately completed exercise preserves the supplied simpler tokenisation.

For an extractive summary, split the complaint into sentences, remove a declared set of stop words from each, count important-word frequencies across that complaint, and score a sentence by the average frequency of its important words. Select the top k with original position as the tie-breaker, then restore original order. Frequency weighting is a heuristic: repeated boilerplate can outrank a critical sentence. Extraction copies source sentences and does not invent new wording, but can omit context, negation or the speaker's main concern.

```text
ALGORITHM SENTIMENT_SCORE
INPUT: complaint, positive words, negative words, negators
OUTPUT: sentiment label and numeric score
BEGIN
    SET total TO 0
    FOR EACH sentence IN complaint DO
        TOKENISE sentence into lowercase words
        FOR EACH word with its position DO
            SET value TO 1 if positive, -1 if negative, otherwise 0
            IF preceding word is a negator THEN
                SET value TO negative value
            ENDIF
            ADD value TO total
        ENDFOR
    ENDFOR
    RETURN positive if total > 0, negative if total < 0, otherwise neutral
END

ALGORITHM EXTRACTIVE_SUMMARY
INPUT: complaint and requested sentence count k
OUTPUT: selected original sentences
BEGIN
    SPLIT complaint into sentences
    IF k <= 0 THEN RETURN empty summary
    ENDIF
    TOKENISE each sentence and REMOVE stop words
    COUNT important-word frequencies across the complaint
    COMPUTE each sentence's average important-word frequency
    RANK sentences by decreasing score, then original position
    SELECT at most k sentences and RESTORE source order
    RETURN selected source sentences
END
```

### A5.2 Rule-based chatbot and limitations
The chatbot accepts PM2.5/PM25, exactly one registered station and either today or an ISO date. It rejects ambiguous station/date requests, validates the calendar date, and executes a parameterised average/count query. An empty result becomes 'No valid readings', never zero pollution. Its reply includes the station, date, mean, physical unit and count. The demonstration fixes today to 2026-10-01 solely for reproducibility; normal execution uses the current date.

```text
ALGORITHM ANSWER_PM25_QUESTION
INPUT: question, station registry, database, current date
OUTPUT: factual answer or clarification
BEGIN
    IF PM2.5 intent is absent THEN RETURN supported-question guidance
    ENDIF
    MATCH registered station names at word boundaries
    IF not exactly one station matches THEN RETURN clarification
    ENDIF
    RESOLVE one explicit valid date OR today
    IF a date cannot be resolved THEN RETURN clarification
    ENDIF
    QUERY average and count using bound station and date parameters
    IF count equals 0 THEN RETURN no-valid-readings message
    ENDIF
    RETURN station, date, mean, unit and valid count
END
```

This system does not understand arbitrary synonyms, Tamil or other languages, misspellings, yesterday/last week, subtle negation, sarcasm, or causal and health questions. The demonstration returns a daily mean, not the latest instantaneous measurement. A complaint with both positive and negative aspects can sum to neutral even when its final opinion is clearly negative.

A trained Naive Bayes alternative would collect independently labelled examples, split training/validation/test data, fit a tokenizer and vocabulary, estimate class priors and token likelihoods, then evaluate macro-F1 and per-class errors on held-out complaints. Inference is roughly O(W*C) for W tokens and C classes, with O(V*C) model memory. The fixed lexicon is O(W) time and O(V_lexicon) dictionary memory, aside from token lists; it needs no training. A language model uses substantially more model memory and compute, with costs depending on architecture and input length. Better accuracy is possible, not guaranteed; domain, language, annotation quality and distribution shift must be tested. No trained-model accuracy is claimed here because no labelled city corpus or model experiment was supplied.
