// src/app/register/register.component.ts
import { Component, EventEmitter, Output } from '@angular/core';
import { AuthService } from '../services/auth.service';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogRef } from '@angular/material/dialog';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [FormsModule, CommonModule],
  styleUrls: ['./register.component.css'],
  templateUrl: './register.component.html'
})
export class RegisterComponent {

  @Output() toggleView = new EventEmitter<void>(); // ✅ Declare output event

  registerData = {
    email: '',
    password: '',
    firstname: '',
    lastname: ''
  };

  message = '';

  constructor(
    private authService: AuthService,
    private router: Router,
    private dialogRef: MatDialogRef<RegisterComponent>) {}

  onRegister() {
    this.authService.register(this.registerData).subscribe({
      next: (res) => {
        this.message = 'Registration successful!';

        this.dialogRef.close();

        this.router.navigate(['/dashboard']);
      },
      error: (err) => {
        console.error(err);
        this.message = err.error.msg || 'Registration failed.';
      }
    });
  }

  onToggleView() {
    this.toggleView.emit(); // ✅ Emit event when toggling view
  }
}
