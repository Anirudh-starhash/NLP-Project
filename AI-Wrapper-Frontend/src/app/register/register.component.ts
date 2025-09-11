// src/app/register/register.component.ts
import { Component } from '@angular/core';
import { AuthService } from '../services/auth.service';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-register',
  standalone: true,
  imports:[CommonModule, FormsModule],
  templateUrl: './register.component.html',
  styleUrls: ['./register.component.css']
})
export class RegisterComponent {

  registerData = {
    firstname: '',
    lastname: '',
    email: '',
    password: '',
    type: 'user',      // Assuming this is required
    profile_pic: ''    // Can be left empty or handled separately
  };

  message = '';

  constructor(private authService: AuthService) {}

  onRegister() {
    this.authService.register(this.registerData).subscribe({
      next: (res) => {
        this.message = res.msg;
      },
      error: (err) => {
        console.error(err);
        this.message = 'Registration failed.';
      }
    });
  }
}
