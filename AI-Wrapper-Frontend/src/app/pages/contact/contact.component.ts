import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-contact',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './contact.component.html',
  styleUrls: ['./contact.component.css']
})
export class ContactComponent {
  onSubmit() {
    // In a real app, you would send this data to a server.
    // For now, we'll just log it to the console.
    console.log('Contact form submitted!');
    alert('Thank you for your message!');
  }
}
