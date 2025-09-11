import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialog } from '@angular/material/dialog'; // 1. Import MatDialog
import { AuthComponent } from '../auth/auth.component';   // 2. Import your AuthComponent

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule], // RouterLink is no longer needed here
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.css']
})
export class HomeComponent {

  // 3. Inject the MatDialog service in the constructor
  constructor(private dialog: MatDialog) {}

  // 4. Create the method to open the dialog
  openDialog(): void {
    this.dialog.open(AuthComponent, {
      width: '450px',
      panelClass: 'auth-dialog-container',
      data: { initialView: 'login' } // Default to the login view
    });
  }
}
