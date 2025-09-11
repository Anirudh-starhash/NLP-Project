import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { MatDialog } from '@angular/material/dialog'; // Import MatDialog
import { AuthComponent } from '../auth/auth.component'; // Import AuthComponent

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [ CommonModule, RouterLink ],
  templateUrl: './header.component.html',
  styleUrls: ['./header.component.css']
})
export class HeaderComponent {
  // Inject the MatDialog service
  constructor(
    public authService: AuthService,
    private router: Router,
    private dialog: MatDialog
  ) {}

  openAuthDialog(view: 'login' | 'register'): void {
    this.dialog.open(AuthComponent, {
      width: '450px',
      panelClass: 'auth-dialog-container', // For custom styling
      data: { initialView: view } // Pass data to the dialog
    });
  }

  logout(): void {
    this.authService.logout();
    this.router.navigate(['/']);
  }
}
