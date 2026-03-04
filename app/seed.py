import json
from main import db, Section, Subsection, Question, app

def seed_data():
    with open('formatted_questions.json', 'r') as f:
        data = json.load(f)
    
    with app.app_context():
        # Clear existing to avoid dupes if running again
        Question.query.delete()
        Subsection.query.delete()
        Section.query.delete()
        
        for s_idx, s_data in enumerate(data):
            section = Section(title=s_data['title'], order=s_idx + 1)
            db.session.add(section)
            db.session.commit()
            
            # Add top-level questions if any
            if 'questions' in s_data and s_data['questions']:
                # For simplicity in current DB schema, we create a dummy subsection for top-level questions
                dummy_sub = Subsection(title="General", section_id=section.id, order=0)
                db.session.add(dummy_sub)
                db.session.commit()
                for q_text in s_data['questions']:
                    q = Question(text=q_text, subsection_id=dummy_sub.id, type='yes_no')
                    db.session.add(q)
            
            # Handle subsections recursively (up to the depth in current data)
            for sub_idx, sub_data in enumerate(s_data.get('subsections', [])):
                process_subsection(sub_data, section.id, sub_idx + 1)
        
        db.session.commit()
        print("Database seeded successfully from Excel data.")

def process_subsection(sub_data, section_id, order):
    subsection = Subsection(title=sub_data['title'], section_id=section_id, order=order)
    db.session.add(subsection)
    db.session.commit()
    
    for q_idx, q_text in enumerate(sub_data.get('questions', [])):
        q = Question(text=q_text, subsection_id=subsection.id, type='yes_no', order=q_idx+1)
        db.session.add(q)
    
    # Nested subsections? Our DB only supports 1 level of Subsection currently.
    # To handle the Excel depth (1.1.1.1), we'll flatten nested titles for now.
    for nested_sub in sub_data.get('subsections', []):
        flattened_title = f"{sub_data['title']} > {nested_sub['title']}"
        nested_db_sub = Subsection(title=flattened_title, section_id=section_id, order=order+100)
        db.session.add(nested_db_sub)
        db.session.commit()
        for q_idx, q_text in enumerate(nested_sub.get('questions', [])):
            q = Question(text=q_text, subsection_id=nested_db_sub.id, type='yes_no', order=q_idx+1)
            db.session.add(q)

if __name__ == '__main__':
    seed_data()
