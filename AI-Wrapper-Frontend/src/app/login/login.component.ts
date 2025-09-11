// src/app/login/login.component.ts
import { Component, EventEmitter, Output } from '@angular/core';
import { AuthService } from '../services/auth.service';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [FormsModule, CommonModule],
  styleUrls: ['./login.component.css'],
  templateUrl: './login.component.html'
})
export class LoginComponent {

  @Output() toggleView = new EventEmitter<void>(); // ✅ Declare output event

  loginData = {
    email: '',
    password: ''
  };

  message = '';

  constructor(private authService: AuthService, private router: Router) {}

  onLogin() {
    this.authService.loginRequest(this.loginData).subscribe({
      next: (res) => {
        localStorage.setItem('access_token', res.access_token);
        localStorage.setItem('user_info', JSON.stringify(res.info));
        this.message = 'Login successful!';
        this.router.navigate(['/dashboard']);
      },
      error: (err) => {
        console.error(err);
        this.message = err.error.message || 'Login failed.';
      }
    });
  }

  onToggleView() {
    this.toggleView.emit(); // ✅ Emit event when toggling view
  }
}
