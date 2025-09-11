// src/app/login/login.component.ts
import { Component } from '@angular/core';
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
        this.router.navigate(['/dashboard']); // or wherever you want to route
      },
      error: (err) => {
        console.error(err);
        this.message = err.error.message || 'Login failed.';
      }
    });
  }
}
