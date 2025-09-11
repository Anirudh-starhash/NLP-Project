import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css']
})
export class DashboardComponent {
  isSidebarOpen = true;
  isDragging = false;
  fileName: string | null = null;





  
  toggleSidebar() {
    this.isSidebarOpen = !this.isSidebarOpen;
  }

  onDragOver(event: DragEvent) {
    event.preventDefault(); // Prevents the browser from opening the file
    this.isDragging = true;
  }

  onDragLeave(event: DragEvent) {
    event.preventDefault();
    this.isDragging = false;
  }

  onDrop(event: DragEvent) {
    event.preventDefault();
    this.isDragging = false;
    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      this.handleFile(files[0]);
    }
  }

  onFileSelected(event: Event) {
    const element = event.currentTarget as HTMLInputElement;
    const files = element.files;
    if (files && files.length > 0) {
      this.handleFile(files[0]);
    }
  }

  private handleFile(file: File) {
    // For now, we'll just log the file and display its name.
    // In a real app, you would start the upload process here.
    if (file.type === "application/pdf") {
      console.log('PDF File selected:', file);
      this.fileName = file.name;
    } else {
      alert('Please select a valid PDF file.');
      this.fileName = null;
    }
  }
}
