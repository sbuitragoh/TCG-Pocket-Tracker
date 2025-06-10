import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class ChartManager:

    def __init__(self, chart_frame):
        self.chart_frame = chart_frame
        self.chart_canvas = None

    def bar_chart(self, labels, owned_pct, missing_pct):

        colors = ["#4caf50", "#e57373"]
        width = 0.5
        x = np.arange(len(labels))

        fig, ax = plt.subplots(figsize=(5, 5))
        owned_bars = ax.bar(x, owned_pct, width, label='Owned', 
                   color=colors[0], alpha=0.8)
        missing_bars = ax.bar(x, missing_pct, width, bottom=owned_pct, 
                            label='Missing', color=colors[1], alpha=0.8)

        for i, (owned_bar, missing_bar) in enumerate(zip(owned_bars, missing_bars)):
            if owned_pct[i] > 5:
                ax.text(owned_bar.get_x() + owned_bar.get_width()/2, owned_pct[i]/2,
                    f'{owned_pct[i]:.1f}%', ha='center', va='center', 
                    fontweight='bold', rotation=90)
            
            if missing_pct[i] > 5:
                ax.text(missing_bar.get_x() + missing_bar.get_width()/2,
                    owned_pct[i] + missing_pct[i]/2, f'{missing_pct[i]:.1f}%',
                    ha='center', va='center', 
                    fontweight='bold', rotation = 90, color="#7c0101")

        ax.set_ylabel('Percentage (%)')
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha='right')
        ax.legend()
        ax.set_ylim(0, 100)

        plt.tight_layout()
        self._update_chart(fig)

    def _update_chart(self, fig):
        chart_frame = self.chart_frame

        if self.chart_canvas:
            self.chart_canvas.get_tk_widget().destroy()
        
        fig.set_size_inches(5, 5)
        
        self.chart_canvas = FigureCanvasTkAgg(fig, master=chart_frame)
        self.chart_canvas.draw_idle()
        self.chart_canvas.get_tk_widget().pack(fill='both', expand=True)
        plt.close(fig)

    def clear_chart(self):

        if self.chart_canvas:
            self.chart_canvas.get_tk_widget().destroy()
            self.chart_canvas = None

