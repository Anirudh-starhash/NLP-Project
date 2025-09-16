import { Component, OnInit, ChangeDetectionStrategy, signal, WritableSignal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';


import { v4 as uuidv4 } from 'uuid';

// Define interfaces for our data structures for type safety
interface PDF {
  file_id: string;
  filename: string;
  upload_time: string;
  filepath: string;
}

interface Message {
  text: string;
  sender: 'user' | 'bot';
  timestamp: string;
}

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl:'../chat/chat.component.html',
  styleUrls:['../chat/chat.component.css'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ChatComponent implements OnInit {
  // --- State Signals ---
  userInput: string = '';
  messages: WritableSignal<Message[]> = signal([]);
  uploadedPdfs: WritableSignal<PDF[]> = signal([]);
  isDocListVisible: WritableSignal<boolean> = signal(false);

  pdf: WritableSignal<PDF | null> = signal(null);
  sessionId: WritableSignal<string> = signal(uuidv4());



  private readonly router = inject(Router);

  constructor(private httpClient:HttpClient){}

  ngOnInit() {
    // In a real app, you would fetch this data from a service
    // that communicates with your backend.
    this.fetchUploadedPdfs();
  }

  fetchUploadedPdfs() {
    const token = localStorage.getItem('access_token'); // get the stored token

    this.httpClient.get('http://localhost:5000/api/get_pdfs', {
      headers: {
        'Authorization': `Bearer ${token}`
      },
      withCredentials: true
    }).subscribe({
      next: (response: any) => {
        this.uploadedPdfs.set(response.pdfs.map((pdf: any) => ({
          ...pdf,
          upload_time: new Date(pdf.upload_time + 'Z').toLocaleString() // Convert to local timezone
        })));
      },
      error: (error) => {
        console.error('Error fetching PDFs', error);
      }
    });
  }

  toggleDocList() {
    this.isDocListVisible.update(visible => !visible);
  }

  getDisplayName(filename: string): string {
    // This regex looks for a UUID at the START of the string, followed by an underscore.
    const uuidRegex = /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}_/;
    return filename.replace(uuidRegex, ''); // Simply replace the matched pattern with an empty string
  }

  selectDocument(pdf: PDF) {
    this.pdf.set(pdf)
    const text = `Querying from document: "${this.getDisplayName(pdf.filename)}"`;
    const newMessage: Message = {
      text: text,
      sender: 'bot',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    this.messages.update(msgs => [...msgs, newMessage]);
    this.isDocListVisible.set(false);

    const token = localStorage.getItem('access_token');
    const endpoint = 'http://localhost:5000/api/prepare_document'; // A proposed endpoint for this action
    const body = { file_id: pdf.file_id };

    this.httpClient.post(endpoint, body, {
      headers: { 'Authorization': `Bearer ${token}` },
      withCredentials: true
    }).subscribe({
      next: (response: any) => {
        // 4a. On SUCCESS, update the message to confirm the document is ready.
        const confirmationText = `Ready to query from document: "${this.getDisplayName(pdf.filename)}"`;

        // Replace the "Preparing..." message with the confirmation.
        this.messages.update(msgs => {
          const lastMsgIndex = msgs.length - 1;
          msgs[lastMsgIndex].text = confirmationText;
          return [...msgs];
        });

        console.log('Backend successfully prepared document:', response);
      },
      error: (err) => {
        // 4b. On ERROR, update the message to inform the user.
        const errorText = `Sorry, there was an error preparing "${this.getDisplayName(pdf.filename)}". Please try again.`;

        this.messages.update(msgs => {
          const lastMsgIndex = msgs.length - 1;
          msgs[lastMsgIndex].text = errorText;
          return [...msgs];
        });
        console.error('Backend error preparing document:', err);
      }
    });
  }

  sendMessage() {
    if (!this.userInput.trim()) return;

    // Add user message
    const userMessage: Message = {
      text: this.userInput,
      sender: 'user',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    this.messages.update(msgs => [...msgs, userMessage]);

    const capturedInput = this.userInput;
    this.userInput = ''; // Clear input immediately

    // Auto-resize textarea back to 1 row
    const textarea = document.querySelector('.query-input') as HTMLTextAreaElement;
    if (textarea) {
        textarea.style.height = 'auto';
    }

     // Detect commands
    if (capturedInput.startsWith('/summary')) {
        this.processSummaryQuery(capturedInput);
    } else {
        // fallback to regular chat
        this.addMessage(capturedInput, 'user');
        this.simulateBotResponse(capturedInput);
    }


    // Simulate bot response



  }

  processSummaryQuery(query: string) {

      const currentPdf = this.pdf();
      this.addMessage(query, 'user');

      const token = localStorage.getItem('access_token');
      const endpoint = 'http://localhost:5000/api/query_document';
      const body = {
        query: query,
        pdf_id:currentPdf?.file_id,
        session_id: this.sessionId()
      };

      this.httpClient.post(endpoint, body, {
          headers: { 'Authorization': `Bearer ${token}` },
          withCredentials: true
      }).subscribe({
          next: (response: any) => {
              this.addMessage(response.answer, 'bot');
          },
          error: (error) => {
              this.addMessage("Error retrieving summary.", 'bot');
              console.error('API error:', error);
          }
      });
  }

  addMessage(text: string, sender: 'user' | 'bot') {
    const msg: Message = {
        text: text,
        sender: sender,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    this.messages.update(msgs => [...msgs, msg]);
  }

  simulateBotResponse(capturedInput:string){
      setTimeout(() => {
      const botResponse: Message = {
        text: `This is a simulated response regarding: "${capturedInput}"`,
        sender: 'bot',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      this.messages.update(msgs => [...msgs, botResponse]);
    }, 1000);
  }

  handleEnter(event: Event) { // <-- 1. Accept the generic Event type
      // 2. Assert that it is a KeyboardEvent before using it
      const keyboardEvent = event as KeyboardEvent;

      if (keyboardEvent.key === 'Enter' && !keyboardEvent.shiftKey) {
          keyboardEvent.preventDefault(); // Prevent new line
          this.sendMessage();
      }
  }

  autoResize(element: HTMLTextAreaElement) {
    element.style.height = 'auto';
    element.style.height = `${element.scrollHeight}px`;
  }

  goBack() {
    this.router.navigate(['/dashboard']);
  }
}
