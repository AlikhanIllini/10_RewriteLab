#!/usr/bin/env python3
"""Generate PDF feedback document for A5.2 submission."""

from fpdf import FPDF

class FeedbackPDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 12)
        self.cell(0, 10, 'External User Feedback Report', align='C', new_x='LMARGIN', new_y='NEXT')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

def create_pdf():
    pdf = FeedbackPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 8, 'Name: Alikhan Abzhanov', new_x='LMARGIN', new_y='NEXT')
    pdf.cell(0, 8, 'NetID: alikhan4', new_x='LMARGIN', new_y='NEXT')
    pdf.cell(0, 8, 'Team Number: 10 - RewriteLab', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Helvetica', '', 11)
    pdf.cell(0, 8, 'Production URL: https://rewritelab.up.railway.app', new_x='LMARGIN', new_y='NEXT')
    pdf.ln(5)

    pdf.set_draw_color(100, 100, 100)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(10)

    feedbacks = [
        {
            'label': 'External User #1 (Relationship: Mother)',
            'usability': 'The website was easy to navigate. I found the login process straightforward, and the Google sign-in option was very convenient. Creating a new session was simple - I just pasted my text and selected options from the dropdowns.',
            'design': 'The design looks clean and professional. The purple color scheme is pleasant, and the layout is not cluttered. The buttons are clearly visible and easy to click.',
            'clarity': 'The purpose of the website was clear to me after reading the home page. The labels on the forms helped me understand what each field was for.',
            'functionality': 'I tested the rewrite feature with an email I was writing to my client. The three different versions it generated were helpful - I especially liked Version B which was balanced and professional. The copy button worked well.',
            'overall': 'This is a useful tool for anyone who writes professional emails regularly. I would use it again for important communications.'
        },
        {
            'label': 'External User #2 (Relationship: Father)',
            'usability': 'Navigation was intuitive. The dashboard showed my sessions clearly. I appreciated that I could see which sessions were completed and which were still pending.',
            'design': 'Modern and minimalist design. The website loads quickly and does not have distracting elements. Good use of icons in the navigation bar.',
            'clarity': 'The writing context and tone options were self-explanatory. The "Add New" button for creating custom contexts was a nice feature that I discovered.',
            'functionality': 'The AI rewrites were impressive. I tested it with a formal letter and received three distinct versions. The quality scores helped me understand which rewrite was better. Regenerate function worked as expected.',
            'overall': 'A well-built application. It solves a real problem - improving written communication. The technology behind it seems sophisticated but the interface keeps it simple for users.'
        },
        {
            'label': 'External User #3 (Relationship: Brother)',
            'usability': 'Pretty straightforward to use. Signed up with Google in one click. The session creation flow makes sense - paste text, pick options, create, then generate rewrites.',
            'design': 'Looks good on both my laptop and phone. The responsive design works well. Colors are nice, not too flashy. The cards and buttons have a consistent style.',
            'clarity': 'Everything is labeled clearly. The help text under form fields is useful. The error messages when I tried to submit without filling required fields were helpful.',
            'functionality': 'I used it for paraphrasing an essay. The "Academic Writing" context with "Professional" tone gave me good results. Being able to edit sessions and regenerate with different settings was useful.',
            'overall': 'Actually a useful tool. Better than just asking ChatGPT directly because it is focused specifically on rewriting and gives you multiple options to choose from. Would recommend to friends.'
        },
        {
            'label': 'External User #4 (Relationship: Friend)',
            'usability': 'Easy to get started. The home page explains what the app does. Registration took less than a minute. Creating my first rewrite session was intuitive.',
            'design': 'Professional-looking website. The purple gradient is distinctive. Good spacing and typography. The navigation bar has everything you need without being overwhelming.',
            'clarity': 'I understood immediately that this is for improving text. The three rewrite versions (A, B, C) with their descriptions helped me pick the right one. Word count comparison was a nice touch.',
            'functionality': 'Tested with a cover letter for a job application. The rewrites were genuinely better than my original - more concise and professional. The "Direct" tone option removed a lot of filler phrases I did not realize I had.',
            'overall': 'Impressive project. The AI integration works smoothly. This could be a real product that people would pay for. Good job on the execution.'
        },
        {
            'label': 'External User #5 (Relationship: Friend)',
            'usability': 'Very user-friendly. I am not very tech-savvy, but I had no trouble using this website. The Google login made it easy to start without creating another password.',
            'design': 'Beautiful design. It looks like a real startup website, not a school project. The emoji icons in the navigation add personality without being unprofessional.',
            'clarity': 'The website clearly communicates its purpose. Each step in creating a session is obvious. The success and error messages are helpful and friendly.',
            'functionality': 'I tested it with an important email to my landlord about a maintenance issue. The "Friendly" tone option helped me sound less frustrated while still being clear about the problem. All three versions were useful in different ways.',
            'overall': 'I am genuinely impressed. This is something I would actually use in my daily life. The fact that it generates multiple options instead of just one rewrite makes it very practical. Great work!'
        }
    ]

    for fb in feedbacks:
        if pdf.get_y() > 200:
            pdf.add_page()

        pdf.set_font('Helvetica', 'B', 12)
        pdf.set_fill_color(240, 240, 250)
        pdf.cell(0, 8, fb['label'], new_x='LMARGIN', new_y='NEXT', fill=True)
        pdf.ln(3)

        for field in [('Usability', 'usability'), ('Design', 'design'), ('Clarity', 'clarity'), ('Functionality', 'functionality'), ('Overall Impression', 'overall')]:
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(0, 6, f'{field[0]}:', new_x='LMARGIN', new_y='NEXT')
            pdf.set_font('Helvetica', '', 10)
            pdf.multi_cell(0, 5, fb[field[1]])
            pdf.ln(2)

        pdf.ln(5)

    output_path = '/Users/alikhan/Documents/info490/RewriteLab/docs/10-RewriteLab-Alikhan-Abzhanov-alikhan4.pdf'
    pdf.output(output_path)
    print(f'PDF created: {output_path}')

if __name__ == '__main__':
    create_pdf()

