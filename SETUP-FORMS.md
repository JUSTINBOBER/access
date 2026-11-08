# Getting booking requests by email

Booking requests from the website are emailed to **pawsandplaypetsoh@gmail.com**.

They go through FormSubmit (formsubmit.co), a free service that needs no account.

## One-time activation (do this once the site is online)

1. Open the live website and send a test booking request.
2. FormSubmit emails **pawsandplaypetsoh@gmail.com** a message titled "Action Required: Activate FormSubmit". Check spam if you don't see it.
3. Click **Activate Form**. Every request after that goes straight to your inbox.
4. Optional: the activation email also gives you a private code (a long random string). To keep your email address out of the form code, paste that code at the top of `script.js`:

   ```js
   const FORMSUBMIT_TO = "your-private-code";
   ```

## What you'll receive

- **Subject:** each email's subject looks like "New request: Overnight stay for Biscuit (Akron), Fri, December 12 – Sun, December 14".
- **Details:** the email has a neat table with the customer's name, email, phone, town, pets, service, dates, walks and notes.
- **Replying:** hitting Reply goes straight to the customer.

## Good to know

- **To change the inbox,** edit `CONTACT_EMAIL` at the top of `script.js`. Then run the activation again for the new address.
- **Spam:** a hidden trap field drops most bot submissions.
- **If sending ever fails,** the visitor sees links to call you or to email you with their request already written out, so nothing gets lost.
- **Prefer Formspree?** Create a form at formspree.io and paste its ID into `FORMSPREE_ID` in `script.js`. It will be used instead.
