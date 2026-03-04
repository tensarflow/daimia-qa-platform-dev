const fs = require('fs');

const rawData = JSON.parse(fs.readFileSync('questions.json', 'utf8'));

const sections = [];
let currentSection = null;
let currentSubsection = null;
let currentSubSubsection = null;

rawData.forEach(row => {
    const text = row["Unnamed: 1"];
    const isQuestion = row["Unnamed: 6"] === ":";

    if (!text) return;

    // Check if it's a main section (e.g., "1. Fahrtzielanzeige", "2. Innenanzeige")
    const sectionMatch = text.match(/^(\d+)\.\s+(.*)/);
    // Check if it's a subsection (e.g., "1.1. Steuergerät")
    const subsectionMatch = text.match(/^(\d+\.\d+)\.\s+(.*)/);
    // Check if it's a sub-subsection (e.g., "1.1.1. Liefergrad")
    const subSubMatch = text.match(/^(\d+\.\d+\.\d+)\.\s+(.*)/);
    // Check if it's a sub-sub-subsection (e.g., "1.1.1.1. EBM")
    const subSubSubMatch = text.match(/^(\d+\.\d+\.\d+\.\d+)\.\s+(.*)/);

    if (isQuestion) {
        const target = currentSubSubsection || currentSubsection || currentSection;
        if (target) {
            if (!target.questions) target.questions = [];
            target.questions.push(text);
        }
    } else if (subSubSubMatch) {
        if (!currentSubSubsection.subsections) currentSubSubsection.subsections = [];
        const sub = { id: subSubSubMatch[1], title: subSubSubMatch[2], questions: [] };
        currentSubSubsection.subsections.push(sub);
    } else if (subSubMatch) {
        if (!currentSubsection.subsections) currentSubsection.subsections = [];
        currentSubSubsection = { id: subSubMatch[1], title: subSubMatch[2], questions: [], subsections: [] };
        currentSubsection.subsections.push(currentSubSubsection);
    } else if (subsectionMatch) {
        if (!currentSection.subsections) currentSection.subsections = [];
        currentSubsection = { id: subsectionMatch[1], title: subsectionMatch[2], questions: [], subsections: [] };
        currentSection.subsections.push(currentSubsection);
    } else if (sectionMatch) {
        currentSection = { id: sectionMatch[1], title: sectionMatch[2], subsections: [], questions: [] };
        sections.push(currentSection);
        currentSubsection = null;
        currentSubSubsection = null;
    }
});

fs.writeFileSync('formatted_questions.json', JSON.stringify(sections, null, 2));
